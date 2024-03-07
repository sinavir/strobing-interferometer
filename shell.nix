{ nixpkgs ? (import ./npins).nixpkgs, pkgs ? import nixpkgs {} }:
let
  archeology = import (pkgs.fetchFromGitHub {
    owner = "NixOS";
    repo = "nixpkgs";
    rev = "5df05c902cde398e056eb6271d5fe13e418db4c6";
    hash = "sha256-5PBcS5ws/6sUMkX6dFzdsnbAb/Y0iZZrbeGHIuZh9Io=";
  }) {};
in
pkgs.mkShell {
  packages = [
    (archeology.python37.withPackages (ps: [
      ps.pyqtgraph
      ps.numpy
      ps.scipy
      ps.pyqt5
    ]))

    archeology.qt5.qtwayland
  ];
  QT_QPA_PLATFORM_PLUGIN_PATH=with archeology; "${qt5.qtbase.bin}/lib/qt-${qt5.qtbase.version}/plugins";
}
