# File format

The python library use the `hdf5` file format to store one acquisition (calibration + strobed videos).

The hdf5 structure is as follow
```plain
TODO batter representtion of attributes

 
file.h5  (2 objects, 6 attributes)
│   ├── duty cycle strobe (%)  5
│   ├── exposure_time_us  15000
│   ├── frame_shape  [1080 1440]
│   ├── laser  L785
│   ├── membrane  topo
│   └── sensing region  1
├── bias calibration  (3 objects)
│   ├── biases  (100,), float64
│   ├── photos  (100, 1080, 1440), float64  # Average of the below videos
│   └── videos  (100, 10, 1080, 1440), uint16
└── stroboscopic  (10 objects, 4 attributes)
    ├── acquisition time  -284.05384135246277
    ├── drive amplitude  0.04999580380099335
    ├── drive frequency  1307205.9200001007
    ├── strobe detuning  0.0799998992588371
    ├── video0  (288, 1080, 1440), uint16
    │   ├── bias(V)  -2.7222222222222223
    │   └── fps  20.0
    ├── video1  (288, 1080, 1440), uint16
    │   ├── bias(V)  -2.166666666666667
    │   └── fps  20.0
    ...
```

You can furthermore explore the file structure with this tool:
[https://myhdf5.hdfgroup.org/](https://myhdf5.hdfgroup.org/)
(It works well even with the 13 gigabytes files the acquisition script produce).

To access the raw data, use the `h5py` library documented here:
[https://docs.h5py.org/](https://docs.h5py.org/).

The analysis tools (to get nice plots of the membrane) are documented in the
[reference](./python_module_reference.md). A more step by step tutorial is
provided in [analysis script explanations](./analysis.md).
