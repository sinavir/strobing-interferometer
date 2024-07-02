# Pinhole alignment protocol

TODO schema

## Light protocol

This protocol is quick. You should do it each time you load a new membrane.

1. Tune the "pinhole" mirror to see the defect on the center of the camera. This
   should correspond to the middle of the pinhole.

2. **Optional** Slightly move the photo-diode to get maximum power. If you lose the photo-diode position it can be hard to get back to it.

## Heavy protocol

This protocol is longer to implement but definitely doable. Aligning a cavity
is highly likely much harder. Apply this protocol if you're not confident about the
location of the pinhole.

1. Examine the setup

2. Remove the pinhole and move the camera so the sensor lands at the place the pinhole was before.

3. Tune the focus lens and the mirror to center the defect on the camera.

4. move the camera back to give some space for the pinhole

5. Draw a cross in ThorCam software on the defect

6. Put the pinhole on the optical path such that you see on the camera the
   bright spot from the pinhole at the exact location of the defect (use the cross drawn at step 5) to help

7. Put back the camera as its original place and center the defect. You can also mark the coordinates of the pinhole on a paper you keep preciously.

8. Put the photo-diode back after the pinhole. It can take a long time to get back some signal since the sensitive region of the photo-diode is small.
