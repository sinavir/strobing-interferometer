import numpy as np
from tqdm.auto import tqdm, trange


class StdAnalysis:

    file_dependent_properties = [
        "calibration_biases",
        "calibration_values",
    ]  # Properties that depend on the hdf5 file

    def __init__(self, file):
        self._file = file

    def file_open(self):
        return self._file

    def file_open_or_fail(self):
        if not self.file_open():
            raise IOError("HDF5 file closed too early")

    def get_calibration_photos(self):
        self.file_open_or_fail()
        return self._file["bias calibration"]["photos"][...]

    def get_calibration_biases(self):
        self.file_open_or_fail()
        return self._file["bias calibration"]["biases"][...]

    def get_videos(self):
        """
        Return a tuple of txo iterators:
            - One yielding the videos
            - One yielding the biases
        """
        self.file_open_or_fail()
        return (
            (  # Use a generator to load lazily the videos
                self._file["stroboscopic"][k][...]
                for k in self._file["stroboscopic"].keys()
            ),
            [
                self._file["stroboscopic"][k].attrs["bias(V)"]
                for k in self._file["stroboscopic"].keys()
            ],
            len(self._file["stroboscopic"].keys()),
        )

    def smooth_calibration(self, window=np.array([0.1, 0.25, 0.3, 0.25, 0.1])):
        """
        Smooth the calibration data points
        """
        if len(window.shape) > 1:
            raise ValueError("Smoothing kernel should be 1-dimensional")

        photos = self.get_calibration_photos()
        biases = self.get_calibration_biases()
        smoothed = np.apply_along_axis(
            lambda x: np.convolve(window, x, mode="valid"), axis=0, arr=photos
        )
        offset = window.size // 2  # number of values missing on each side

        self.calibration_biases = biases[offset:-offset]
        self.calibration_values = smoothed

    def compute_calibration_slopes(self):
        self.calibration_slopes = np.array(
            np.gradient(self.calibration_values, axis=0)
        )  # TODO: Provide X values for the gradient

    @staticmethod
    def std_image(video):
        """
        Compute the single video phase image
        """
        std = np.std(video, axis=0)

        # Get coordinates of the brightest pixel
        bightest_pixel: tuple[int, int] = np.unravel_index(
            np.argmax(std, axis=None), std.shape
        )  # pyright: ignore

        transposed_normalized_video = np.transpose(
            video - np.mean(video, axis=0), (1, 2, 0)
        )

        brightest_pixel_time_trace = transposed_normalized_video[
            bightest_pixel[0], bightest_pixel[1], :
        ]

        video_dot: np.ndarray = np.dot(
            transposed_normalized_video, brightest_pixel_time_trace
        )
        return np.where(video_dot > 0, std, -std)

    ## Function that takes in an HDF5 file and returns a list of calibrated videos.
    def compute_independant_video_images(self):
        videos, specific_biases, video_number = self.get_videos()

        def find_nearest(array, value):
            idx = np.searchsorted(array, value, side="left")
            if idx > 0 and (
                idx == len(array)
                or np.abs(value - array[idx - 1]) < np.abs(value - array[idx])
            ):
                return idx - 1
            return idx

        # Find the indices in calibration_* arrays corresponding to the videos
        specific_biases_indices = np.array(
            [
                find_nearest(self.calibration_biases, specific_bias)
                for specific_bias in specific_biases
            ]
        )
        specific_biases_calibration_slope: np.ndarray = (
            1 / self.calibration_slopes[specific_biases_indices, :, :]
        )

        std_images = np.array(
            [
                self.std_image(video)
                for video in tqdm(
                    videos,
                    total=video_number,
                    desc="Processing videos",
                )
            ]
        )
        print("Applying calibration sign...", end="")
        std_images_phase_calibrated = std_images * np.where(
            specific_biases_calibration_slope > 0, 1, -1
        )
        std_images_full_calibrated = std_images * specific_biases_calibration_slope
        print("Done")
        self.fully_calibrated_images = (
            std_images_full_calibrated  # Phase+amplitude # TODO
        )
        self.phase_corrected_images = std_images_phase_calibrated  # phase only
        self.calibration_slopes_video_indexed = self.calibration_slopes[
            specific_biases_indices
        ]

    def combine_images(self):
        """
        Combine images
        """
        absolute_slopes = np.abs(self.calibration_slopes_video_indexed)
        to_flip = np.array(
            [
                np.vdot(
                    self.phase_corrected_images[0, :, :],
                    self.phase_corrected_images[i, :, :],
                )
                for i in trange(0, self.phase_corrected_images.shape[0])
            ]
        )
        corrected_photos: np.ndarray = np.where(
            to_flip[:, None, None] > 0,
            self.fully_calibrated_images,
            -self.fully_calibrated_images,
        )

        # Initialize empty images
        self.mode_image = np.empty(corrected_photos.shape[1:])
        self.best_video_index = np.empty(corrected_photos.shape[1:], dtype=np.uint64)
        # For each pixel get the best video time trace
        with np.nditer(
            self.mode_image, flags=["multi_index"], op_flags=["writeonly"]
        ) as it:
            for pixel in tqdm(it, total=self.mode_image.size):
                best_video = np.argmax(
                    absolute_slopes[:, it.multi_index[0], it.multi_index[1]]
                )
                pixel[...] = corrected_photos[
                    best_video, it.multi_index[0], it.multi_index[1]
                ]
                self.best_video_index[it.multi_index[0], it.multi_index[1]] = best_video
