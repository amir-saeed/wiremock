poetry run pip install `
    "--platform" "manylinux2014_x86_64" `
    "--implementation" "cp" `
    "--python-version" "3.12" `
    "--abi" "cp312" `
    "--only-binary=:all:" `
    "--target" "$stagingDir" `
    "--upgrade" `
    "-r" "requirements.txt"