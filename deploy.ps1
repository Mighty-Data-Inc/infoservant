./venv/scripts/Activate.ps1
powershell.exe -noninteractive -command remove-item build -recurse
powershell.exe -noninteractive -command remove-item dist -recurse
powershell.exe -noninteractive -command remove-item *.eggo-info -recurse
pip install wheel twine
python setup.py sdist bdist_wheel
twine upload dist/* --verbose
