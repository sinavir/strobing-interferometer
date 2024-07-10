{
  lib,
  buildPythonPackage,
  setuptools,
  breakpointHook,
    pyqtgraph
 ,   pyqt5
 ,   numpy
 ,   scipy
 ,   tqdm
 ,   thorlabs_tsi_sdk
 ,   h5py
}:

let
  removeFilesets = lib.foldl lib.fileset.difference;
in

buildPythonPackage {
  pname = "arkheon";
  version = "unstable-2024-02-27";
  pyproject = true;

  src =
    ./..;

    nativeBuildInputs = [ setuptools
  breakpointHook
  ];

  propagatedBuildInputs = [
    pyqtgraph
    pyqt5
    numpy
    scipy
    tqdm
    thorlabs_tsi_sdk
    h5py
  ];

  doCheck = false;

  meta = with lib; {
    #license = licenses.eupl12;
    maintainers = with maintainers; [ ];
  };
}
