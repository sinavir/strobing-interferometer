{ nixpkgs ? (import ../npins).nixpkgs, pkgs ? import nixpkgs {} }:
let
  inherit (pkgs) lib;
  inherit (lib) fileset;
  root = filter: fileset.toSource {
    root = ./.;
    fileset = filter (fileset.intersection (fileset.gitTracked ../.) (fileset.fileFilter (file: ! file.hasExt "nix") ./.));
  };
in
rec {
  dll-linux = pkgs.stdenv.mkDerivation (finalAttrs: {
    name = "thorcam-lib";
    src = ./prebuilt;
    nativeBuildInputs = [ pkgs.autoPatchelfHook ];
    buildInputs = [
      pkgs.udev
      pkgs.stdenv.cc.cc.lib
    ];
    installPhase = ''
      mkdir -p $out/lib
      install -m755 ./*.so $out/lib
    '';
  });
  windows = pkgs.pkgsCross.mingwW64.stdenv.mkDerivation ({
    name = "strobing-interferometer-windows";
    TARGET = "Windows_NT";
    src = root (orig: orig);
    installPhase = ''
      mkdir -p $out/bin
      install -m 755 ./bin/* $out/bin
      install -m 755 ./prebuilt/*.dll $out/bin
    '';
  });
  linux = pkgs.stdenv.mkDerivation ({
    name = "strobing-interferometer-linux";
    TARGET = "Linux";
    src = root (orig: fileset.difference orig (fileset.unions [
      ./prebuilt
    ]));
    buildInputs = [
      dll-linux
      pkgs.openblas
    ];
    installPhase = ''
      mkdir -p $out/bin
      install -m 755 ./bin/* $out/bin
    '';
  });
}
