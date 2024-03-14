{ nixpkgs ? (import ../npins).nixpkgs, pkgs ? import nixpkgs {} }:
pkgs.mkShell {
  packages = [
  ];
  shellHook = ''
    # fixes libstdc++ issues and libgl.so issues
    LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/:${pkgs.udev}/lib
  '';
}
