{ nixpkgs ? (import ./npins).nixpkgs, pkgs ? import nixpkgs { config.allowUnfree = true; } , old ? false}:
let
  archeology = if old then
  import (pkgs.fetchFromGitHub {
    owner = "NixOS";
    repo = "nixpkgs";
    rev = "5df05c902cde398e056eb6271d5fe13e418db4c6";
    hash = "sha256-5PBcS5ws/6sUMkX6dFzdsnbAb/Y0iZZrbeGHIuZh9Io=";
  }) { config.allowUnfree = true; } else pkgs;
  libthorlabs_tsi_sdk = (archeology.callPackage ./nix/libthorlabs.nix {});
in
pkgs.mkShell {
  nativeBuildInputs = [
    ((if old then archeology.python37 else archeology.python311).withPackages (ps: [
      ps.pyqtgraph
      ps.numpy
      ps.scipy
      ps.pyqt5
      ps.ipython
      ps.tqdm
      ps.h5py
      ps.ipympl
      ps.matplotlib
      ps.jupyter
      (ps.callPackage ./nix/thorcam.nix { inherit libthorlabs_tsi_sdk; })
    ]))

    pkgs.vale
    (pkgs.python3.withPackages (p: [
      p.mkdocs
      p.mkdocs-material
      p.mkdocstrings
      p.mkdocstrings-python
    ]))


    archeology.qt5.qtwayland
  ];
  QT_QPA_PLATFORM_PLUGIN_PATH=with archeology; "${qt5.qtbase.bin}/lib/qt-${qt5.qtbase.version}/plugins";
  # Hack for old nixpkgs because i didn't manage to put this folder in RPATH
  LD_LIBRARY_PATH="${libthorlabs_tsi_sdk}/lib";

}
