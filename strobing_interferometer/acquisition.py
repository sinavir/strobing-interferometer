import time
from pathlib import Path
from typing import Union, Tuple

import h5py
import numpy as np
from HF2 import HF2  # pyright: ignore # TODO: use zhinsts directly
from RigolDG1032Z.rigol1032 import DG1032Z  # pyright: ignore
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
from tqdm.auto import tqdm, trange


class InstrumentManager:
    """
    Class to manage the instruments
    """

    default_manager = None
    rigol_addr = "TCPIP0::10.209.65.139::inst0::INSTR"
    rigol_channel = 1
    bias_gain = 0.1

    hf2_serial = "dev1224"
    camera_sn = "25779"

    @classmethod
    def get_default(cls):
        if cls.default_manager is not None:
            return cls.default_manager
        cls.default_manager = cls()
        return cls.default_manager

    # TODO: camera_lock = None

    def __init__(self):
        self.rigol = DG1032Z(self.rigol_addr)
        self.rigol.channel = self.rigol_channel
        self.hf2 = HF2(self.hf2_serial, 1)

    def get_drive_freq(self):
        return self.hf2.daq.getDouble("/dev1224/oscs/0/freq")

    def get_strobe_frequency(self):
        return self.hf2.daq.getDouble("/dev1224/sigouts/0/amplitudes/6")

    def get_drive_amplitude(self):
        return self.rigol.frequency

    def set_freqs(self, x, detun=1):
        """
        Function to set the drive frequency and the detuning of the strobing

        This function doesn't turn on the strobing.

        Args:
            freq (float): The drive frequency
            detun (float): The detuning of the strobe
        """
        self.hf2.daq.setDouble("/dev1224/oscs/0/freq", x)
        self.rigol.frequency = x + detun

    def strobe_at(self, detun: float = 1.0):
        """
        Function that retrieves the drive frequency and set the strobe frequency

        This function doesn't turn on the strobing.

        Args:
            detun (float): The strobe detuning (positive means strobing at higher frequency)
        """
        f = self.hf2.daq.getDouble("/dev1224/oscs/0/freq")
        self.rigol.frequency = f + detun

    def strobe_on(self):
        self.rigol.output = True

    def strobe_off(self):
        self.rigol.output = False

    def drive_on(self):
        self.hf2.daq.setInt("/dev1224/sigouts/0/enables/6", 1)

    def drive_off(self):
        self.hf2.daq.setInt("/dev1224/sigouts/0/enables/6", 0)

    def goToBias(self, new_bias, speed=0.1, step_size=0.005):
        """
        Function to go smoothly from one bias value to another

        speed in 10V/s
        step in 10V
        """
        delta_t = step_size / speed
        old_bias = self.hf2.daq.getDouble("/dev1224/sigouts/1/offset") / self.bias_gain
        span = abs(new_bias - old_bias)
        n_step = int(np.ceil(span / step_size))  # pyright: ignore  # pyright is drunk
        steps = np.linspace(old_bias, new_bias, n_step)
        for b in steps:
            self.hf2.daq.setDouble("/dev1224/sigouts/1/offset", b * self.bias_gain)
            time.sleep(delta_t)


class Acquisition:
    path = None

    def __init__(
        self,
        path: Union[Path, str],
        exposure_time_us: int,
        n_calib: int,
        bias_range: Tuple[float, float],
        vid_len: int = 288,
        strobe_detuning: float = 0.5,
        instruments_manager=None,
        **kwargs,
    ):
        self.path = Path(path)
        if self.path.is_dir():
            self.path = self.path
        if self.path.exists():
            raise ValueError(
                "The target file for the acquisition already exists ({})".format(
                    str(self.path)
                )
            )

        self.acquisition_kwargs = kwargs

        self.strobe_detuning = strobe_detuning
        self.vid_len = vid_len
        self.exposure_time_us = exposure_time_us
        self.n_calib = n_calib
        if bias_range[0] >= bias_range[1]:
            raise ValueError("Please provide a valid bias range")
        self.bias_range = bias_range
        if instruments_manager is None:
            self.instruments_manager = InstrumentManager.get_default()
        else:
            self.instruments_manager = instruments_manager

        self.kwargs = kwargs

    def acquire_calibration(self):
        """
        Record bias calibration. This will use several gigas of RAM.

        Should not be used while the thorcam software is open
        """

        self.biases = np.linspace(self.bias_range[0], self.bias_range[1], 100)

        biases = self.biases

        self.instruments_manager.strobe_at(detun=2000)

        self.instruments_manager.drive_off()

        self.instruments_manager.goToBias(biases[0], speed = 1.0)

        time.sleep(1)

        with TLCameraSDK() as sdk:  # TODO: move the camera handling logic to the instument_manager
            available_cameras = sdk.discover_available_cameras()
            if len(available_cameras) < 1:
                raise Exception("no cameras detected")

            with sdk.open_camera(self.instruments_manager.camera_sn) as camera:
                camera.image_poll_timeout_ms = 100
                camera.exposure_time_us = self.exposure_time_us

                camera.frames_per_trigger_zero_for_unlimited = 1
                frame_shape = (
                    camera.sensor_height_pixels,
                    camera.sensor_width_pixels,
                )

                # exposure time sanity check
                print("Exposure time sanity check...", end="")
                camera.arm(2)
                camera.issue_software_trigger()
                frame = None
                t0 = time.time()
                while frame is None:
                    if time.time() - t0 > 2:
                        print(
                            "The frame I'm waiting may have been dropped. Do not hesitate to stop the script if you think it is the case"
                        )
                    frame = camera.get_pending_frame_or_null()

                print("Done")
                n_saturating = np.sum(np.array(frame.image_buffer) > 1020)
                frame_max = np.max(frame.image_buffer)
                print("Number of saturating pixels:", n_saturating)
                if (
                    n_saturating > 50000
                ):  # arbitrary (= few percent of the image are saturating)
                    raise Exception("Saturating image.please decrease exposure time")
                if frame_max < 1000:
                    raise Exception("Too dim image.please increase exposure time")
                camera.disarm()

                print("Acquiring calibration data")
                buffer = np.empty(
                    (len(biases), self.n_calib, *frame_shape), dtype=np.uint16
                )
                with h5py.File(self.path, "a") as f:
                    camera.frames_per_trigger_zero_for_unlimited = self.n_calib
                    camera.arm(2)
                    for i, bias in tqdm(enumerate(biases), total=len(biases)):
                        self.instruments_manager.goToBias(bias)
                        time.sleep(0.05)
                        camera.issue_software_trigger()
                        prev_frame = None
                        for j in range(camera.frames_per_trigger_zero_for_unlimited):
                            frame = None
                            while frame is None:
                                frame = camera.get_pending_frame_or_null()
                            buffer[i, j] = frame.image_buffer
                            if (
                                prev_frame is not None
                                and frame.frame_count - prev_frame > 1
                            ):
                                raise Exception(
                                    "Dropped frame at bias n°{i} (Bias={bias})"
                                )
                            prev_frame = frame.frame_count
                    camera.disarm()
                    f.attrs["frame_shape"] = np.array(frame_shape)
                    f.attrs.update(self.kwargs)
                    grp = f.create_group("bias calibration")
                    grp.create_dataset("photos", data=np.mean(buffer, axis=1))
                    grp.create_dataset("videos", data=buffer, dtype=np.uint16)
                    grp.create_dataset("biases", data=biases)

        print("Please turn on the drive and find the right frequency")

    def acquire_modeshape(self):
        freq = self.instruments_manager.get_drive_freq()

        biases_vid = np.array([self.biases[10 * i + 5] for i in range(10)])

        self.instruments_manager.strobe_on()
        self.instruments_manager.strobe_at(detun=0.5)

        time.sleep(1)

        begin_time = time.time()

        strobe_attrs = {
            "strobe detuning": self.instruments_manager.get_strobe_frequency() - freq,
            "drive amplitude": self.instruments_manager.get_drive_amplitude(),
            "drive frequency": freq,
        }

        self.instruments_manager.goToBias(biases_vid[0])

        print(f"Saving to `{self.path}`")
        with TLCameraSDK() as sdk:
            available_cameras = sdk.discover_available_cameras()
            if len(available_cameras) < 1:
                print("no cameras detected")
            else:
                with sdk.open_camera(self.instruments_manager.camera_sn) as camera:

                    camera.image_poll_timeout_ms = 1000
                    camera.exposure_time_us = self.exposure_time_us

                    camera.frame_rate_control_value = 20

                    cam_shape = (
                        self.vid_len,
                        camera.sensor_height_pixels,
                        camera.sensor_width_pixels,
                    )

                    buffer = np.empty((len(biases_vid), *cam_shape), dtype=np.uint16)

                    with h5py.File(self.path, "a") as f:
                        if "stroboscopic" in f:
                            del f["stroboscopic"]
                        grp = f.create_group("stroboscopic")
                        grp.attrs.update(strobe_attrs)
                        buffer = np.empty(cam_shape)
                        n_video = len(biases_vid)
                        for i, bias in enumerate(biases_vid):
                            print("Going to right bias...", end="")
                            self.instruments_manager.goToBias(bias)
                            print(" Sleeping...", end="")
                            time.sleep(3)  # TODO: make tunable
                            print(" Arming camera...")
                            camera.frames_per_trigger_zero_for_unlimited = self.vid_len
                            # This buffer size comes from thorlabs' live camera example. Let's keep it
                            camera.arm(2)
                            camera.issue_software_trigger()
                            prev_frame = None
                            for j in trange(
                                self.vid_len, desc=f"Video n°{i}/{n_video}"
                            ):
                                frame = None
                                while frame is None:
                                    frame = camera.get_pending_frame_or_null()
                                buffer[j] = frame.image_buffer
                                if (
                                    prev_frame is not None
                                    and frame.frame_count - prev_frame > 1
                                ):
                                    raise Exception(
                                        f"Dropped frame at bias n°{i} (Bias={bias})"
                                    )
                                prev_frame = frame.frame_count
                            fps = camera.get_measured_frame_rate_fps()  # TODO: fix
                            print("Disarming... ", end="")
                            camera.disarm()
                            print("Saving...")
                            dset = grp.create_dataset(
                                f"video{i}", data=buffer, dtype=np.uint16
                            )
                            dset.attrs["fps"] = fps
                            dset.attrs["bias(V)"] = bias
                            f.flush()
                        grp.attrs["acquisition time"] = begin_time - time.time()
        print("Data acquisition is succesfully completed.")
