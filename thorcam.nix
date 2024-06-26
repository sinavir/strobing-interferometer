{
  lib,
  fetchzip,
  buildPythonPackage,
  setuptools,
  numpy,
  stdenv,
  udev,
  unzip,
  autoPatchelfHook,
}:

buildPythonPackage rec {
  pname = "thorlabs_tsi_sdk";
  version = "0.0.8";

  src = fetchzip {
    url = "https://www.thorlabs.com/software/THO/ThorCam/Programming/Scientific_Camera_Interfaces_Linux-2.1.zip";
    hash = "sha256-sfWUvjYhM5qb18jLDFWtozJRq5Kaf/Mtw9vSBOMi4P8=";
  };

  sourceRoot = ".";

  postUnpack = ''
    unzip source/SDK/Python_Toolkit/thorlabs_tsi_camera_python_sdk_package.zip
    cd thorlabs_tsi_sdk-0.0.8
  '';

  prePatch = ''
    mv ../source/SDK/Native_Toolkit/bin/Native_64_lib/libthorlabs_tsi_*.so thorlabs_tsi_sdk/
    rm -r thorlabs_tsi_sdk.egg-info
  '';
    
  patches = [ ./01-thorcam.patch ];

  nativeBuildInputs = [ setuptools autoPatchelfHook unzip ];

  propagatedBuildInputs = [
    numpy
  ];
  buildInputs = [
    udev
    stdenv.cc.cc.lib
  ];

  meta = with lib; {
    description = "";
    homepage = "";
    license = licenses.unfree;
    maintainers = with maintainers; [];
  };
}
