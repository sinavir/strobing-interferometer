import numpy as np
import scipy
from tqdm.auto import tqdm, trange


class StdAnalysis:
    """
    Standard analysis class.

    There is a bunch of instance variables that represent the different steps of the analysis.
    These variables are None by default. As you run the different functions of the class, these variables will get populated.

    There is a special `StdAnalysis.compute_all()` function that will perform the whole analysis.

    If you want to adapt this class to another file format than the default
    hdf5 format from the original project, you can subclass the class and
    override all the functions that access to `StdAnalysis._file` to ada pt to
    your custom file format.
    """

    calibration_biases = None
    "Calibration bias values"

    calibration_values = None
    "Pictures of the membrane at each calibration bias"

    calibration_slopes = None
    "Slopes of the calibration curves"

    fully_calibrated_images = None
    phase_corrected_images = None
    calibration_slopes_video_indexed = None

    mode_image = None
    "Mode image not masked with the membrane shapes"

    best_video_index = None
    "indices of video with the bigest interferometer sensitivity for each camera pixel"

    mask = None
    "Membrane shape mask"

    masked_image = None
    "Mode image masked using `self.mask`"

    clipped_image = None
    "Mode image with extreme values removed"

    def __init__(self, file):
        """
        Initialise the analysis class.

        Args:
            file (h5py.File): A hdf5 file handle (for instance
        """
        self._file = file

    @property
    def is_open(self):
        return self._file

    def file_open_or_fail(self):
        """
        Check if file is open or fail with `IOError`
        """
        if not self.is_open:
            raise IOError("HDF5 file closed too early")

    def get_calibration_photos(self):
        self.file_open_or_fail()
        return self._file["bias calibration"]["photos"][...]

    def get_calibration_biases(self):
        self.file_open_or_fail()
        return self._file["bias calibration"]["biases"][...]

    def get_videos(self):
        """
        Return a tuple of two generators:
            - One yielding the videos
            - One yielding the biases

        These generators can't outlive the file handle
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
        Smooth the calibration data points.

        Sets `self.calibration_biases` and `self.calibration_values` to
        respectively the biases values and the smoothed pixel intensity values.

        Args:
            window (np.ndarray): The kernel for the smoothing


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
        """
        Sets `self.calibration_slopes` to the slopes of calibration curves
        """
        if self.calibration_values is None:
            raise Exception("")
        self.calibration_slopes = np.array(
            np.gradient(self.calibration_values, axis=0)
        )  # TODO: Provide X values for the gradient

    @staticmethod
    def std_image(video):
        """
        Compute the mode shape (with phase) image for a single video.

        It performs the following actions:
            - Compute the stddev of each pixel along time
            - Look at pixel wih the largest stddev. It is taken as a reference
            - For each pixel time trace we compute the dot product along time
              with the reference pixel time trace. This dot product inform use
              on the phase of this point of the membrane with respect to the
              reference pixel
                - If the dot product is negative we put `- std(pixel time trace)` on the image
                - Else we put `std(pixel time trace)` on the image

        Args:
            video (np.ndarray): The raw video from the camera.
        Returns:
            np.ndarray: `± std(video, axis=time)`. The ± is determined according to the phase with respect to the reference pixel time trace
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
        """
        Apply `self.std_images` to each video and then apply a proportional
        correction using the calibration data to correct
          1. the spatial intensity variation of the laser
          2. the position on the interference fringe (if light intensity
             increase or decrease when the membrane displacement increase).

        The result is stored in `self.fully_calibrated_images`

        We also store the image apply only the second correction to `self.phase_corrected_images`
        """

        if self.calibration_slopes is None:
            raise Exception("")

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
        std_images_phase_calibrated = std_images * np.where(
            specific_biases_calibration_slope > 0, 1, -1
        )
        std_images_full_calibrated = std_images * specific_biases_calibration_slope
        self.fully_calibrated_images = std_images_full_calibrated  # Phase+amplitude
        self.phase_corrected_images = std_images_phase_calibrated  # phase only
        self.calibration_slopes_video_indexed = self.calibration_slopes[
            specific_biases_indices
        ]

    def combine_images(self):
        """
        Combine images.

            1. Flip the phase of some images so that all the images show the same global phase
            2. For each pixel take the value from the most sensitive video shot (according to calibration data)
        """
        if self.fully_calibrated_images is None:
            raise Exception("")
        if self.phase_corrected_images is None:
            raise Exception("")
        if self.calibration_slopes_video_indexed is None:
            raise Exception("")
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
            -self.fully_calibrated_images,  # pyright: ignore
        )

        # Initialize empty images
        self.mode_image = np.empty(corrected_photos.shape[1:])
        self.best_video_index = np.empty(corrected_photos.shape[1:], dtype=np.uint64)
        # For each pixel get the best video time trace
        with np.nditer(
            self.mode_image,
            flags=["multi_index"],
            op_flags=["writeonly"],  # pyright: ignore
        ) as it:
            for pixel in tqdm(it, total=self.mode_image.size):
                best_video = np.argmax(
                    absolute_slopes[:, it.multi_index[0], it.multi_index[1]]
                )
                pixel[...] = corrected_photos[  # pyright: ignore
                    best_video, it.multi_index[0], it.multi_index[1]
                ]
                self.best_video_index[it.multi_index[0], it.multi_index[1]] = best_video

    def apply_membrane_shape_masking(self, threshold=1.0, sigma=100):
        """
        Compute the membrane shape in `self.mask`.

        The term sensitivity refers to the amplitude of the calibration data curve.

        Algorithm:
            - For each pixel:
                1. Compute the average sensitivity in the nearby area (typical size of `sigma` pixels)
                2. Pick this pixel as a pixel from the membrane if the pixel sensitivity is greater than 
        """
        if self.calibration_values is None:
            raise Exception("")
        sensitivity = np.std(self.calibration_values, axis=0)
        smoothed = scipy.ndimage.gaussian_filter(sensitivity, sigma=sigma)
        self.mask = sensitivity > (threshold * smoothed)
        self.masked_image = self.mode_image * self.mask

    def clip_high_values(self, percentile=99.0):
        if self.masked_image is None:
            raise Exception("")
        k = np.percentile(np.abs(self.masked_image[~np.isnan(self.masked_image)]), percentile)
        self.clipped_image = np.clip(self.masked_image, -k, k)

    def compute_all(self):
        self.smooth_calibration()
        self.compute_calibration_slopes()
        self.compute_independant_video_images()
        self.combine_images()
        self.apply_membrane_shape_masking()
        self.clip_high_values()
