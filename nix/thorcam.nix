{
  lib,
  fetchzip,
  buildPythonPackage,
  setuptools,
  numpy,
  unzip,
  libthorlabs_tsi_sdk,
}:

buildPythonPackage rec {
  pname = "thorlabs_tsi_sdk";
  version = "0.0.8";

  src = fetchzip (import ./thorlabs_tsi_sdk_sources.nix);

  sourceRoot = ".";

  postUnpack = ''
    unzip source/SDK/Python_Toolkit/thorlabs_tsi_camera_python_sdk_package.zip
    cd thorlabs_tsi_sdk-0.0.8
  '';

  prePatch = ''
    rm -r thorlabs_tsi_sdk.egg-info
    sed -i -E 's#LoadLibrary\(r"(.+\.so)"\)#LoadLibrary(r"${libthorlabs_tsi_sdk}/lib/\1")#' thorlabs_tsi_sdk/*.py
  '';

  nativeBuildInputs = [ setuptools unzip ];

  propagatedBuildInputs = [
    numpy
  ];

  meta = with lib; {
    description = "";
    homepage = "";
    license = licenses.unfree;
    maintainers = with maintainers; [];
  };
}
