# Mở Chrome riêng cho việc thu thập (profile riêng, ngoài repo), điều khiển được qua CDP tại 127.0.0.1:9222.
# Người dùng tự đăng nhập Facebook trong cửa sổ này (một lần; profile giữ phiên đăng nhập).
$prof = "$env:LOCALAPPDATA\RoxanaMonitor\chrome-profile"
New-Item -ItemType Directory -Force $prof | Out-Null
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
Start-Process -FilePath $chrome -ArgumentList @(
  "--remote-debugging-port=9222", "--remote-debugging-address=127.0.0.1", "--user-data-dir=`"$prof`"",
  "--no-first-run", "--no-default-browser-check", "--window-size=1400,1000",
  # Không cho Chrome ngừng vẽ khi cửa sổ bị che — nếu không, lệnh chụp màn hình bị treo.
  "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
  "--disable-background-timer-throttling", "--disable-features=CalculateNativeWinOcclusion",
  "https://www.facebook.com/")
