# Record bias calibration. Be aware this will use a lot of RAM.
# Please close thorcam software
# BEGIN of tunables

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

exposure_time_us = 40

CAMERA_SN = "25779"

with TLCameraSDK() as sdk:
    available_cameras = sdk.discover_available_cameras()
    if len(available_cameras) < 1:
        print("no cameras detected")
    else:
        with sdk.open_camera(CAMERA_SN) as camera:

            app = pg.mkQApp("ImageItem Example")

            ## Create window with GraphicsView widget
            win = pg.ImageView()
            win.show()  ## show widget alone in its own window
            win.setWindowTitle("Thorcam")
            roi = pg.RectROI([20, 20], [20, 20], pen=(0, 9))

            win.view.addItem(roi)

            timer = QtCore.QTimer()
            timer.setSingleShot(True)

            def updateData():
                global img, prev_frame
                frame = camera.get_pending_frame_or_null()
                if frame is not None:
                    if prev_frame is not None and frame.frame_count - prev_frame > 1:
                        pass
                        # print(f"Dropped {frame.frame_count - prev_frame - 1}")
                    prev_frame = frame.frame_count
                    win.setImage(
                        np.copy(frame.image_buffer.T),
                        autoRange=False,
                        autoLevels=False,
                        autoHistogramRange=False,
                        levels=(0, 1024),
                    )
                    if win.image is not None:
                        image = win.getProcessedImage()
                        colmaj = win.imageItem.axisOrder == "col-major"
                        if colmaj:
                            axes = (win.axes["x"], win.axes["y"])
                        else:
                            axes = (win.axes["y"], win.axes["x"])
                        data, coords = roi.getArrayRegion(
                            image.view(np.ndarray),
                            img=win.imageItem,
                            axes=axes,
                            returnMappedCoords=True,
                        )
                        if data is not None:
                            print("{:>20.5f}".format(np.sum(data)))
                    ## Display the data
                timer.start(1)

            timer.timeout.connect(updateData)

            # camera
            camera.image_poll_timeout_ms = 1
            camera.exposure_time_us = exposure_time_us
            prev_frame = None

            camera.frames_per_trigger_zero_for_unlimited = 0
            camera.arm(2)
            camera.issue_software_trigger()

            updateData()

            pg.exec()
