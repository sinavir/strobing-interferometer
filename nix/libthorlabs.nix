{ stdenv, fetchzip, udev,  autoPatchelfHook,
 }:
stdenv.mkDerivation {

  pname = "libthorlabs_tsi_sdk";
  version = "0.0.8";
  src = fetchzip (import ./thorlabs_tsi_sdk_sources.nix);

  nativeBuildInputs = [ autoPatchelfHook ];

  buildInputs = [
    udev
    stdenv.cc.cc.lib
  ];

  installPhase = ''
    mkdir -p $out/lib
    export appendRunpaths=("$out/lib")
    export runtimeDependencies=("$out")
    install -m755 SDK/Native_Toolkit/bin/Native_64_lib/libthorlabs_tsi_*.so $out/lib
  '';
}
