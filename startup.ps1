$arguments = '-Command','mitmdump -q -s ''{0}''' -f (Join-Path -Path $pwd.Path -ChildPath main.py)
Start-Process powershell.exe -ArgumentList $arguments -Wait -WorkingDirectory (Get-Location).Path -Verb RunAs
