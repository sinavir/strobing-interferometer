{ nixpkgs ? <nixpkgs>, pkgs ? import nixpkgs {} }:
pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (ps: [
      ps.pyqtgraph
      ps.numpy
      ps.scipy
      ps.pyqt5
    ]))

    pkgs.qt5.qtwayland
  ];
  QT_QPA_PLATFORM_PLUGIN_PATH=with pkgs; "${qt5.qtbase.bin}/lib/qt-${qt5.qtbase.version}/plugins";
}
