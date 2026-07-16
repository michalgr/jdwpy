{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.jdk
    pkgs.lsof
    pkgs.uv
  ];

  shellHook = ''
    echo "===================================================="
    echo "Welcome to the jdwpy development environment!"
    echo "Available tools:"
    echo "  - java, javac, jdb ($(java -version 2>&1 | head -n 1))"
    echo "  - lsof ($(lsof -v 2>&1 | head -n 1 | cut -d ' ' -f 1-3))"
    echo "  - uv ($(uv --version))"
    echo "===================================================="
  '';
}
