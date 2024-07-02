# Alignment frequently asked questions

## Why is the imaging setup tilted

We tilted it to get rid of reflections on the vacuum chamber glass.

!!! note
    The main beam-splitter in the black box is also tilted.
    This is because we observed also less parasitic reflections doing so.

## Can I move this lens or mirror

Only of you know what you are doing. The hardest part to align are (in decreasing difficulty):

1. **Pinhole + Photo-diode + Pinhole Camera**: This part isn't so tricky but
    can take a long time to inexperienced hands. Please follow the protocol
    [here](./pinhole_alignment.md) to realign.

    !!! warning
        Moving the lenses on the pinhole alignment might be tricky. We don't now
        to what extend the cropped beam (by the pinhole) move when doing so and if it remains
        in the sensitive region of the photo-diode. Anyway, if you feel you lost some
        signal while doing so, move slightly the **photo-diode** to get
        signal back. **Don't move the camera and the pinhole in this case**, else you are
        good to follow the protocol [here](./pinhole_alignment.md).

2. **Laser beam** Getting the laser beam hitting the membrane in a nice way can
    take time. If you don't see fringes it means the
    you are in the situation depicted in the following figure.

    TODO schema

3. **Imaging setup** You can move this part of the setup. It's not difficult to align
    if you understand how a camera+objective setups works. We encourage you to move the mirror between
    the objective and the camera to tune your image.

## Too much fringes on the membrane

The membrane isn't parallel to the back-glass slab. Please read the documentation [here](TODO) to correct that.
