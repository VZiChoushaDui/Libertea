<img src="https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/logo-complete.png" style="width: 300px" />

# Libertea

سرور V2ray VPN چند مسیری را به راحتی نصب و مدیریت کنید. با مدیریت کاربر، استتار دامنه، و به روز رسانی خودکار مسیرها برای کاربران.

[中文 چینی](https://github.com/VZiChoushaDui/Libertea/blob/master/README-zh.md)

[English](https://github.com/VZiChoushaDui/Libertea/blob/master/README.md)

## امکانات

- پروتکل های **TROJAN**، **Shadowsocks/v2ray** و **VLESS** (نیرو گرفته توسط پروژه XRay)
- **استتار دامنه** با یک وب سایت واقعی برای کاهش خطر مسدود شدن با کاوش
- نصب و مدیریت **تک دستوری**
- پشتیبانی از **چندین** دامنه و IP و **انتخاب خودکار** بهترین مسیر در دستگاه های کاربر
- **مدیریت چند کاربره** با محدودیت اتصال

## پیکربندی حداقلی

- سروری که Ubuntu 20.04+ یا Debian 11+ را اجرا می کند (اوبونتو 22.04 توصیه می شود)
- حداقل 1 گیگابایت رم
- یک دامنه/زیر دامنه به یک CDN (مانند Cloudflare) اشاره دارد و CDN روی حالت SSL «Full» تنظیم شده است.

## پیکربندی توصیه شده

- دو دامنه پشت CDN (مانند Cloudflare)، یکی برای پنل/به روز رسانی و دیگری برای خود VPN
- یک یا چند سرور اضافی برای پراکسی ثانویه (512 مگابایت رم برای پراکسی های ثانویه کافی است)

## نصب و راه اندازی

1. یک دامنه بخرید و DNS آن را روی یک CDN (مانند Cloudflare) قرار دهید و CDN را روی حالت «Full» SSL قرار دهید. [راهنما](https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/cloudflare-full-ssl.png)

2. آدرس IP سرور خود را روی رکورد DNS CDN تنظیم کنید و مطمئن شوید که CDN فعال است. (نماد ابر نارنجی در Cloudflare)

3. دستور زیر را روی سرور خود اجرا کنید و دستورالعمل ها را دنبال کنید.

       curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh install

    *نصب ممکن است چند دقیقه طول بکشد.*

## به روز رسانی

برای به روز رسانی کافیست دستور زیر را روی سرور خود اجرا کنید:

    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh update

## حذف

اگر به هر دلیلی می خواهید Libertea یا Libertea-secondary-proxy را از سرور خود حذف کنید، دستور زیر را روی سرور خود اجرا کنید:

    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh uninstall

## مشارکت

ما از مشارکت در Libertea استقبال می‌کنیم! لطفاً برای هر گونه اشکال، پیشرفت و ایده، یک issue  باز کنید. یا اگر می‌خواهید در توسعه Libertea کمک کنید، یک درخواست Pull باز کنید. اگر در حال باز کردن یک درخواست Pull هستید، مطمئن شوید که آن را به شاخه development این مخزن ارسال کنید.

## سوالات متداول

##### آیا Libertea دامنه ها و IP های من را از مسدود شدن در امان نگه می دارد؟

پروژه Libertea از پروتکل های مبتنی بر SSL استفاده می کند، بنابراین ترافیک از ترافیک معمولی HTTPS قابل تشخیص نیست. همچنین با تنظیم دامنه Camouflage در نصب Libertea، خطر کاوش فعال کاهش می یابد. با این حال، GFW ممکن است پس از مدتی همچنان دامنه ها و IP های شما را بر اساس استفاده مسدود کند. توصیه می شود از دامنه های *چند* و پراکسی های ثانویه استفاده کنید و به صورت دوره ای آی پی های پروکسی ثانویه خود را تغییر دهید.

##### آیا می توانم ترافیک منطقه ای را مستقیماً (بدون عبور از VPN) مسیریابی کنم؟

بله. در پنل مدیریت، به تب *Settings* بروید و در قسمت *Route regional IPs directly*، کشورهایی را که می خواهید مستقیماً از آنها عبور کنید را انتخاب کنید.

##### برخی از سرورها یا برنامه های CDN من ترافیک محدودی دارند. آیا می توانم سرورها را اولویت بندی کنم؟

بله. شما می توانید برای هر دامنه و پراکسی ثانویه یک اولویت تعیین کنید. دستگاه‌های کاربران ابتدا مسیرهای با اولویت بالاتر را امتحان می‌کنند و تنها در صورت در دسترس نبودن از مسیرهای با اولویت پایین‌تر استفاده می‌کنند. به این ترتیب، می توانید میزان مصرف ترافیک خود را در هر سرور/دامنه با توجه به نیاز خود بهینه کنید.

##### آیا می‌توانم گواهی SSL خودم را استفاده کنم؟

بله. Libertea به‌طور پیش‌فرض گواهی را با Let's Encrypt صادر می‌کند. اگر Let's Encrypt در دسترس نباشد، یا از قبل گواهی دارید، یک فایل PEM ترکیبی (زنجیره کامل گواهی و سپس کلید خصوصی) را در این مسیر قرار دهید:

    /root/libertea/certs/<your-domain>.pem

نام فایل باید دقیقاً همان دامنه باشد (مثلاً `/root/libertea/certs/vpn.example.com.pem`). Libertea این فایل را در HAProxy نصب می‌کند و برای آن دامنه Let's Encrypt را صدا نمی‌زند. برای بازگشت به Let's Encrypt، فایل را حذف کنید.

برای ساخت PEM ترکیبی:

    cat fullchain.pem privkey.pem > /root/libertea/certs/vpn.example.com.pem

##### Docker Hub / GitHub / PyPI مسدود است، یا اینترنت ایران قطع شده. چطور نصب کنم؟

نصب پیش‌فرض از رجیستری‌های عمومی (اوبونتو، Docker Hub، PyPI و `docker compose`) استفاده می‌کند. اگر این‌ها در دسترس نیستند (مثلاً در قطعی سراسری)، پروفایل شبکه محدود را فعال کنید:

    ./init.sh install --iran-blackout

`--restricted-network` همان فلگ است. در `bootstrap.sh` آن را بعد از دستور بگذارید (`install --iran-blackout`، `update --iran-blackout`، `install-proxy … --iran-blackout`).

**خود لیبرتیا هم از GitHub می‌آید**، پس در قطعی کامل باید فایل‌ها را خودتان روی سرور بگذارید: آن‌ها را در `/root/libertea` کپی کنید (مثلاً آرشیوی از یک سیستم با دسترسی سالم) و بعد از همان مسیر `./init.sh install --iran-blackout` را اجرا کنید. `bootstrap.sh` هم با فایل‌های از قبل آماده کار می‌کند: اگر به GitHub نرسد، به‌جای خطا از همان فایل‌های موجود استفاده می‌کند.

اگر `github.com`، `pypi.org` و `archive.ubuntu.com` در یک بررسی کوتاه (~۵ ثانیه) شکست بخورند، نصب‌کننده از شما می‌خواهد `iran` را تایپ کنید تا این پروفایل فعال شود، یا Enter بزنید تا رد شود. به‌روزرسانی‌های بعدی اگر فایل `.libertea.iran` وجود داشته باشد همان پروفایل را نگه می‌دارند.

حالت قطعی ایران نمی‌تواند از GitHub دانلود کند. نصب‌کننده **متوقف می‌شود** مگر این فایل از قبل موجود باشد (یا sing-box ۱.۱۳.۱ روی میزبان نصب شده باشد):

    providers/outbound-direct/sing-box

این فایل باید **sing-box 1.13.1** برای همین CPU باشد (amd64 یا arm64). در صورت نیاز PEM ترکیبی را در `certs/<domain>.pem` بگذارید (سؤال SSL بالاتر).

`--iran-blackout` فقط روی میزبان اعمال می‌شود و برگشت‌پذیر است: apt به `ir.archive.ubuntu.com`، یک drop-in برای systemd-resolved در `/etc/systemd/resolved.conf.d/libertea-restricted-dns.conf`، pip از ایندکس Liara، و Docker به‌صورت `docker.io` + compose v1 با آینه Arvan. Dockerfileهای پیش‌فرض روی Docker Hub می‌مانند.

بعد از رفع قطعی، ابتدا فایل نشانه را حذف کنید تا به‌روزرسانی‌های بعدی از این پروفایل استفاده نکنند، سپس drop-in DNS را حذف و resolved را ری‌استارت کنید:

    rm -f /root/libertea/.libertea.iran
    rm -f /etc/systemd/resolved.conf.d/libertea-restricted-dns.conf
    systemctl restart systemd-resolved

حذف نصب (uninstall) هم این drop-in را برمی‌دارد و sources.list پشتیبان‌گیری‌شده را برمی‌گرداند.
