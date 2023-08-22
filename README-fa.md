<img src="https://raw.githubusercontent.com/quiniapiezoelectricity/Libertea/master/docs/logo-complete.png" style="width: 300px" />

# Libertea

سرور V2ray VPN چند مسیری را به راحتی نصب و مدیریت کنید. با مدیریت کاربر، استتار دامنه، و به روز رسانی خودکار مسیرها برای کاربران.

[中文 چینی](https://github.com/quiniapiezoelectricity/Libertea/blob/master/README-zh.md)

[English](https://github.com/quiniapiezoelectricity/Libertea/blob/master/README.md)

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

       curl -s https://raw.githubusercontent.com/quiniapiezoelectricity/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh install

    *نصب ممکن است چند دقیقه طول بکشد.*

## به روز رسانی

برای به روز رسانی کافیست دستور زیر را روی سرور خود اجرا کنید:

    curl -s https://raw.githubusercontent.com/quiniapiezoelectricity/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh update

## حذف

اگر به هر دلیلی می خواهید Libertea یا Libertea-secondary-proxy را از سرور خود حذف کنید، دستور زیر را روی سرور خود اجرا کنید:

    curl -s https://raw.githubusercontent.com/quiniapiezoelectricity/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh uninstall

## مشارکت

ما از مشارکت در Libertea استقبال می‌کنیم! لطفاً برای هر گونه اشکال، پیشرفت و ایده، یک issue  باز کنید. یا اگر می‌خواهید در توسعه Libertea کمک کنید، یک درخواست Pull باز کنید. اگر در حال باز کردن یک درخواست Pull هستید، مطمئن شوید که آن را به شاخه development این مخزن ارسال کنید.

## سوالات متداول

##### آیا Libertea دامنه ها و IP های من را از مسدود شدن در امان نگه می دارد؟

پروژه Libertea از پروتکل های مبتنی بر SSL استفاده می کند، بنابراین ترافیک از ترافیک معمولی HTTPS قابل تشخیص نیست. همچنین با تنظیم دامنه Camouflage در نصب Libertea، خطر کاوش فعال کاهش می یابد. با این حال، GFW ممکن است پس از مدتی همچنان دامنه ها و IP های شما را بر اساس استفاده مسدود کند. توصیه می شود از دامنه های *چند* و پراکسی های ثانویه استفاده کنید و به صورت دوره ای آی پی های پروکسی ثانویه خود را تغییر دهید.

##### آیا می توانم ترافیک منطقه ای را مستقیماً (بدون عبور از VPN) مسیریابی کنم؟

بله. در پنل مدیریت، به تب *Settings* بروید و در قسمت *Route regional IPs directly*، کشورهایی را که می خواهید مستقیماً از آنها عبور کنید را انتخاب کنید.

##### برخی از سرورها یا برنامه های CDN من ترافیک محدودی دارند. آیا می توانم سرورها را اولویت بندی کنم؟

بله. شما می توانید برای هر دامنه و پراکسی ثانویه یک اولویت تعیین کنید. دستگاه‌های کاربران ابتدا مسیرهای با اولویت بالاتر را امتحان می‌کنند و تنها در صورت در دسترس نبودن از مسیرهای با اولویت پایین‌تر استفاده می‌کنند. به این ترتیب، می توانید میزان مصرف ترافیک خود را در هر سرور/دامنه با توجه به نیاز خود بهینه کنید.
