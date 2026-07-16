{
  description = "Asynchronous JDWP implementation in Python";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.uv
            pkgs.jdk
            pkgs.lsof
          ];

          shellHook = ''
            echo "===================================================="
            echo "Welcome to the jdwpy development environment (Flake)!"
            echo "Available tools:"
            echo "  - java: $(java -version 2>&1 | head -n 1)"
            echo "  - uv:   $(uv --version)"
            echo "===================================================="
          '';
        };
      }
    );
}
