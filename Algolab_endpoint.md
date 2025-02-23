
Genel Bilgilendirme
Versiyon: 1.0.5
Api Yetkilendirilmesi
API anahtarınızı Algolab üzerinden başvuru yapıp aldıktan sonra, Deniz Yatırım API ile bu dökümantasyonda yer alan yönlendirmelere göre uygulamanızı geliştirebilirsiniz. Her kullanıcı için bir adet API Anahtarı oluşturulmaktadır.

Başvurunun Onaylanması 
Başvurunuzun onaylanabilmesi için başvuru yaptığınız kısmın altında nasıl tamamlayacağınız belirtilen Uygunluk ve Yerindelik testleri en az Yüksek(4) olacak şekilde (Yerindelik testi sonunda yer alan Yatırım Danışmanlığı Çerçeve Sözleşmesi de onaylanmalı) tamamlanmalı ve Algoritmik İşlem Sözleşmesi onaylanmalıdır.
Canlı Veri Tipleri 
Anlık veri erişimi için iki adet izin mevcuttur. Bu izinler şu şekilde açıklanmaktadır:

Canlı Veri Sözleşmesi: Soketten gelen verilerin anlık olarak gelmesi için gerekli olan sözleşmedir. Eğer canlı veri yetkiniz bulunmuyorsa 15 dakika gecikmeli olarak belirli aralıklarla gelmektedir.

Derinlik Veri Sözleşmesi: Soketten gelen derinlik verilerine erişim sağlayan sözleşmedir. On kademe alım satım derinliği sağlanmaktadır.

API’ yi kullanırken lütfen aşağıdaki bilgileri unutmayın:

APIKEY: Rastgele bir algoritma tarafından oluşturulan API işlemlerinin kimliğidir.

Internet Bankacılığı Kullanıcı Adı/TCK Numarası: İnternet bankacılığına giriş yaparken sizin oluşturduğunuz kullanıcı adı veya internet bankacılığına giriş yaparken kullandığınız TCK numaranız.

Internet Bankacılığı Şifreniz: Sizin oluşturmuş olduğunuz internet bankacılığı şifreniz.

Sms Doğrulama Kodu: Sistemde kayıtlı telefon numaranıza gelen rastgele oluşturulmuş şifredir.

Etkileşim Talebi
Bu bölüm temel olarak erişime odaklanmaktadır:

Rest-API istekleri için aşağıdaki url ile erişim sağlanmaktadır.
   https://www.algolab.com.tr/api
Soket bağlantısı için aşağıdaki url ile erişim sağlanmaktadır.
   wss://www.algolab.com.tr/api/ws
API Doğrulaması
Bir istek başlatmak için aşağıdaki bilgiler gerekmektedir;
APIKEY: API Anahtarıdır.
Authorization: Kullanıcı girişi yapıldıktan sonraki isteklerde kullanılmaktadır.
Checker: Her isteğe özel imzadır. Her isteğe göre yeniden oluşturulur. APIKEY + RequestPath + QueryString veya Body(GET/POST Methoduna göre değişiklik göstermektedir.)
RequestPath: API yolu.
QueryString: İstek URL’ indeki sorgu dizesi (?’den sonraki istek parametresi soru işareti ile birlikte)
Body: İstek gövdesine karşılık gelen dize. Body genellikle POST isteğinde olur.



Kullanıcı Girişi: SMS Alma
Internet Bankacılığı bilgileri ile giriş yapmanızı sağlar. İstek sonunda sistemde kayıtlı telefon numaranıza SMS doğrulama kodu gelir. Gelen SMS’ teki kod ile bir sonraki işlem gerçekleştirilecektir.

Http İsteği

POST /api/LoginUser
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan APIKEY
İstek Parametresi

Aşağıdaki parametreleri AES Algoritmasını kullanarak APIKEY içerisindeki “-” ‘den sonraki string değer ile şifrelemeniz gerekmektedir.

Örneğin:

APIKEY: APIKEY-XXXXXXXXXXX

Yukarıdaki APIKEY’ e göre AES Algoritmasında kullanılacak key aşağıdaki şekildedir.

aes.Key: xxxxxxxxxx

 

İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
Username	String	Kullanıcı Adı/ TCK Numarası
Password	String	İnternet Bankacılığı Şifresi
 

Örnek Request Body

{
   "Username": "XXXXXXXX==",
   "Password": "XXXXXXXX=="
}

 

Sonuç Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
token	String	SMS için gerekli token
 

 Örnek Response

{
   "success": true,
   "message": "",
   "content": {
      "token": "Ys/WhU/xxxxxxxxxxxMlzyb3TKJVWxLlpb/xxxxxxxxxx"
   }
}

Kullanıcı Girişi: Oturum Açma
Kullanıcı girişi Sms alma metodunda alınan token ve sistemdeki kayıtlı telefonunuza gelen kod ile hash kodu almanızı sağlar.

Http İsteği: POST /api/LoginUserControl
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
 

İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
token	String	SMS Alma metotundaki token
Password	String	SMS Kodu
Örnek Request Body

{
   "token": "Ys/WhU/xxxxxxxxxxxMlzyb3TKJVWxLlpb/xxxxxxxxxx",
   "Password": "9LHZEiA2AhKsAtM4yOOrEw=="
}

 

Sonuç Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
Hash	String	Oturum süresi boyunca erişim sağlanacak oturum anahtarıdır.
 

Örnek Response:

{
   "success": true,
   "message": "",
   "content": {
      "hash": "eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1NiIsInR5cCI6IkpX VCJ9.eyJBdXRob3JpemF0aW9uIjoiQXV0aG9yaXplZCIsIkN1c3RvbWVyTm8iOiIxMzQ1MTcyMCIsIk5ld3NsZXR0ZXIi OiJUcnVlIiwiSXNCbG9ja2VkIjoiRmFsc2UiLCJFbWFpbCI6IjEzNDUxNzIwIiwiVXNlcklkIjoiMTAxIiwiRGVuaXpiYW5rIjoi VHJ1ZSIsIm5iZiI6MTY1MzQ4NjMxMCwiZXhwIjoxNjUzNTcyNzEwfQ.8PtF5zNa24bSr3edBuqzpeWqbgxK2rLRXQReovoC2c"
   }
}

Oturum Yenileme
Oturum yenileme fonksiyonudur.

Http İsteği: POST /api/ SessionRefresh
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek Parametresi herhangi bir parametre almamaktadır.

 

Sonuç Bool(true,false) değer döner.


Sembol Bilgisi
Sembol ile ilgili bilgileri getirir.

Http İsteği: POST /api/GetEquityInfo
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek Parametreleri 

Parametre Adı	Parametre Tipi	Açıklama
symbol	String	Sembol Kodu
Örnek Request Body

{
   "symbol": "TSKB"
}

 

Sonuç Parametreleri 

Parametre Adı	Parametre Tipi	Açıklama
name	String	Sembol Adı
flr	String	Taban
clg	String	Tavan
ask	String	Alış Fiyatı
bid	String	Satış Fiyatı
lst	String	Son Fiyat
limit	String	İşlem Limiti
min	String	-
max	String	-
step	String	-
Örnek Response

{
   "success": true,
   "message": "",
   "content": {
      "name": "TSKB",
      "flr": "1.840",
      "clg": "2.240",
      "ask": "2.060",
      "bid": "2.050",
      "lst": "2.060",
      "limit": "0.00",
      "min": "",
      "max": "",
      "step": ""
   }
}

Alt Hesap Bilgileri
Kullanıcıya ait alt hesap bilgilerini getirir.

Http İsteği: POST /api/GetSubAccounts
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek parametresi bulunmamaktadır.

 

Sonuç Parametreleri 

Parametre Adı	Parametre Tipi	Açıklama
Number	String	Alt Hesap Numarası
TradeLimit	String	Alt Hesap İşlem Limiti
Örnek Response

{
   "success": true,
   "message": "",
   "content": [
      {
         "number": "100",
         "tradeLimit": "1000.00"
      },
      {
         "number": "101",
         "tradeLimit": "2000.00"
      }
   ]
}

Hisse Portföy Bilgisi
Kullanıcıya ait anlık portföy bilgilerini getirir.

Http İsteği: POST /api/InstantPosition
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
Subaccount	String	
Alt Hesap Numarası (Boş olarak gönderilebilir,

boş olarak gönderilirse Aktif Hesap bilgilerini iletir.)

Örnek Request Body

{
  "Subaccount": ""
}

 

Sonuç Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
maliyet	String	
Menkul kıymetin alış fiyatı

totalstock	String	Menkul kıymetin Toplam Miktarı
code	String	Enstrüman ismi
profit	String	Menkul Kıymet Kar/Zararı
cost	String	Menkul kıymetin birim maliyeti
unitprice	String	Menkul kıymetin birim fiyatı
totalamount	String	Toplam satır bakiye TL değeri
tlamount	String	TL tutarı
explanation	String	Menkul kıymet Açıklaması
type	String	Overall kaleminin tipi
total	String	-
Örnek Response

{
  "success": true,
  "message": "",
  "content": [
    {
      "maliyet": "2.05",
      "totalstock": "1",
      "code": "TSKB",
      "profit": "0",
      "cost": "2.05",
      "unitprice": "2.05",
      "totalamount": "",
      "tlamaount": "2.05",
      "explanation": "TSKB",
      "type": "CH",
      "total": "0"
    }
  ]
}

Hisse Özeti
Kullanıcıya ait Hisse özet bilgilerini getirir.

Http İsteği: POST /api/RiskSimulation
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
Subaccount	String	
Alt Hesap Numarası (Boş olarak gönderilebilir,

boş olarak gönderilirse Aktif Hesap bilgilerini iletir.)

Örnek Request Body

{
  "Subaccount": ""
}

 

Sonuç Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
t0

String

T Nakit Bakiyesi

t1

String

T+1 Nakit Bakiyesi

t2

String

T+2 Nakit Bakiyesi

t0stock

String

-

t1stock

String

-

t2stock

String

-

t0equity

String

 T Hisse Portföy Değeri  

t1equity

String

T+1 Hisse Portföy Değeri 

t2equity

String

T+2 Hisse Portföy Değeri 

t0overall

String

T Overall Değeri Nakit Dahil

t1overall

String

T+1 Overall Değeri Nakit Dahil 

t2overall

String

T+2 Overall Değeri Nakit Dahil 

t0capitalrate

String

T Özkaynak Oranı  

t1capitalrate

String

T+1 Özkaynak Oranı 

t2capitalrate

String

T+2 Özkaynak Oranı 

netoverall

String

Nakit Hariç  Overall 

shortfalllimit

 String 

Açığa satış sözleşmesi olan müşteriler için kullanılabilir açığa satış bakiyesi 

credit0

String 

T Kredi Bakiyesi 

Örnek Response

{
  "success": true,
  "message":  "",
  "content": [
    {
      "t0": "0",
      "t1": "0",
      "t2": "0",
      "t0stock": "0",
      "t1stock": "0",
      "t2stock": "0",
      "t0equity": "0",
      "t1equity": "0",
      "t2equity": "0",
      "t0overall": "0",
      "t1overall": "0",
      "t2overall": "0",
      "t0capitalrate": "0",
      "t1capitalrate": "0",
      "t2capitalrate": "0",
      "netoverall": "0",
      "shortfalllimit": "0",
      "credit0": "0"
    }
  ]
}

Hisse Günlük İşlemler
Kullanıcıya ait günlük işlem kayıtlarını getirir.

Http İsteği: POST /api/TodaysTransaction
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
Subaccount	String	
Alt Hesap Numarası (Boş olarak gönderilebilir,

boş olarak gönderilirse Aktif Hesap bilgilerini iletir.)

Örnek Request Body

{
  "Subaccount": ""
}

 

Sonuç Parametreleri 

Parametre Adı	Parametre Tipi	Açıklama
atpref	String	Referans Numarası
ticker	String	Hisse Senedi İsmi
buysell	String	İşlemin Cinsi (Alış, Satış)
ordersize	String	Emir Miktarı
remainingsize	String	Emrin BIST’ te henüz karşılanmamış
ve kalan bölümü bu sahada belirtilir.
price	String	Emrin ortalama gerçekleşme fiyatını
belirtir.
amount	String	Gerçekleşen kısım ile ilgili müşterinin hesabından çekilecek
veya hesabına yatırılacak meblağ bu
sahada bulunmaktadır.
transactiontime	String	Emrin giriş tarihini belirtir. Kısa tarih
formatındadır.
timetransaction	String	Emrin girildiği tarih uzun tarih
formatındadır.
valor	String	Emrin geçerliliğinin başladığı seans tarihini belirtir. Kısa tarih
formatındadır.
status	String	Emrin değiştirilebilme durumu bilgilerini içerir; Emir Silme,
İyileştirme ve valör iptali
işlemlerinin yapılıp yapılamayacağı bu bilgilerden anlaşılır. 5 haneden oluşan bir “string” değerdir. Her bir karakter “0” (“Mümkün Değil”) veya
“1” (“Mümkün”) olabilir. Soldan
itibaren birinci değer emrin silinip silinemeyeceğini belirtir. İkinci ve üçüncü değerler fiyat iyilestirme ve emir bölme işlemlerinin yapılıp yapılamayacağını belirtir. Sonraki değer ise emrin geçerlilik süresinin iptal edilip edilemeyeceğini belirtir.
En son değer emrin kötüleştirilip
kötüleştirilemiyeceğini belirtir.
waitingprice	String	Emrin bekleyen kısmının fiyatını belirtir. Emir fiyatı olarak bu alan kullanılmalıdır.
description	String	
Emir durumu bilgisini belirtir;

İletildi
Silindi
İyileştirme Talebi Alındı
İyileştirildi
Silme Talebi Alındı
İyileştirme Reddedildi
Emir Reddedildi
Silme Reddedildi
KIE Emri Silindi
KPY Emri Silindi
Gerçekleşti
Kısmi Gerçekleşti
transactionId	String	GTP’de tutulan referansı belirtir. İşlemler GTP’ye bu referans gönderilir. GTP emri bu id ile tanır. GTP’de unique olarak tutulur.
equityStatusDescription	String	
Ekranda emirleri gruplayabilmek amaçıyla gönderilen özel bir alandır.

WAITING: Bekleyen Emirler
DONE: Gerçekleşen Emirler
PARTIAL: Kısmi Gerçekleşen Emirler
IMPROVE_DEMAND: Emir iyileştirme talebi alındı
DELETE_DEMAND: Emir silme talebi alındı
DELETED: Gerçekleşmesi olmayan silinmiş emirler, borsadan red almış emirler.
shortfall	String	Açığa satış
timeinforce	String	Emrin geçerlilik süresini belirtir. Emir girişinde kullanılan değerler
geri dönülür.
fillunit	String	Gerçekleşme adet bilgisini verir.

Örnek Response

{
  "success": true,
  "message": "",
  "content": [
    {
      "atpref": "0013O2",
      "ticker": "TSKB",
      "buysell": "Alış",
      "ordersize": "1",
      "remainingsize": "0",
      "price": "2.050000",
      "amount": "2.050000",
      "transactiontime": "27.05.2022 00:00:00",
      "timetransaction": "27.05.2022 11:47:32",
      "valor": "27.05.2022",
      "status": "00000",
      "waitingprice": "2.050000",
      "description": "Gerçekleşti",
      "transactionId": "0000-291B5D-IET",
      "equityStatusDescription": "DONE",
      "shortfall": "0",
      "timeinforce": "",
      "fillunit": "1"
    }
  ]
}

Emir Gönderim
Alım/satım emrini iletir.

Http İsteği: POST /api/SendOrder
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
symbol	String	Sembol Kodu
direction	String	BUY/SELL
pricetype	String	Emir Tipi (piyasa/limit)
price	String	Emir tipi limit ise fiyat girilmelidir.(örneğin 1.98)
lot	String	Emir adedi
sms	Bool	Sms Gönderim
email	Bool	Email Gönderim
Subaccount	String	Alt Hesap Numarası (Boş gönderilebilir. Boş gönderilirse Aktif Hesap Bilgilerini Getirir.)
Örnek Request Body

{
  "symbol": "TSKB",
  "direction": "BUY",
  "pricetype": "limit",
  "price": "2.01",
  "lot": "1",
  "sms": true,
  "email": false,
  "Subaccount": ""
}

 

Emir doğru bir şekilde iletilmiş ise sistemden String olarak emir referans numarası dönmektedir. Aşağıdaki örnek response içinde yer alan işaretli numara ile emrinizi düzenleyebilir veya silebilirsiniz.

Örnek Response

{
  "success": true,
  "message": "",
  "content": "Referans Numaranız: 001VEV;0000-2923NR-IET - HISSEOK"
}



Nakit Bakiye
T0, T+1, T+2 nakit bayileri getirir.

Http İsteği: POST /api/CashFlow
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
Subaccount	String	
Alt Hesap Numarası (Boş olarak gönderilebilir,

boş olarak gönderilirse Aktif Hesap bilgilerini iletir.)

Örnek Request Body

{
  "Subaccount": ""
}

 

Sonuç Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
t0	String	
T+0 Anındaki Nakit Bakiye

t1	String	T+1 Anındaki Nakit Bakiye
t2	String	T+2 Anındaki Nakit Bakiye
Örnek Response

{
  "success": true,
  "message": "Canceled",
  "content": {
    "t0": "",
    "t1": "",
    "t2": ""
  }
}

Hesap Ekstresi
Kullanıcıya ait ilgili tarihler arasındaki hesap ekstresini verir.

Http İsteği: POST /api/AccountExtre
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
start	DateTime	Başlangıç Tarihi
end	DateTime	Bitiş Tarihi
Subaccount	String	
Alt Hesap Numarası (Boş olarak gönderilebilir,

boş olarak gönderilirse Aktif Hesap bilgilerini iletir.)

Örnek Request Body

{
   "start": 2023-07-01 00:00:00,
   "end": 2023-07-31 00:00:00,
   "Subaccount": ""
}

 

Sonuç Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
accountextre	List<AccountExtre>	Hisse Ekstre
viopextre	List<ViopAccountStatement>	Viop Ekstre
 

Account Extre

Parametre Adı	Parametre Tipi	Açıklama
transdate	String	İşlemin muhasebe tarihi
explanation	String	İşlemin açıklaması
debit	String	İşlem ile ilgili borç miktarı
credit	String	İşlem ile ilgili alacak miktarı
balance	String	İşlem sonrasındaki hesabın bakiyesi
valuedate	String	İşlemin valör tarih ve saati
 

Viop Account Statement

Parametre Adı	Parametre Tipi	Açıklama
shortlong	String	Uzun kısa (Alış\Satış) sözleşme bilgisi
transactiondate	String	Emir zamanı
contract	String	İşlem yapılan sözleşme adı
credit	String	Alınan miktar
debit	String	Satılan miktar
units	String	Sözleşme adedi
price	String	Sözleşme fiyatı
balance	String	Hesap Bakiyesi
currency	String	Para birimi
Örnek Response

{
  "success": True,
  "message": "",
  "content": {
    "accountextre": [
      {
        "transdate": "01.01.0001 00:00:00",
        "explanation": "Devir",
        "debit": "0",
        "credit": "0",
        "balance": "0",
        "valuedate": "22.07.2024 00:00:00"
      }
    ],
    "viopextre": [
      {
        "shortlong": "-",
        "transactiondate": "-",
        "contract": "-",
        "credit": "-",
        "debit": "-",
        "units": "-",
        "price": "-",
        "balance": "Object reference not set to an instance of an object.",
        "currency": "-"
      }
    ]
  }
}

Hisse Emri İptal Etme
Gönderilen ve açık olan hisse emrini iptal eder.

Http İsteği: POST /api/DeleteOrder
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

 İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
id	String	Emrin ID’ si
subAccount	String	Alt Hesap Numarası (Boş gönderilebilir. Boş gönderilirse Aktif Hesap Bilgilerini Getirir.)
Örnek Request Body

{
   "id": "001VEV",
   "subAccount": ""
}

 

Sonuç Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
message	String	Emrin iletimi hakkında bilgi verir.
duration	String	-
Örnek Response

{
   "success": true,
   "message": "Success",
   "content": {
      "message": "Success",
      "duration": "-"
   }
}


Emir İyileştirme
Gönderilen ve açık olan emiri iyileştirir.

Http İsteği: POST /api/ModifyOrder
Http Headers Content-Type: application/json
APIKEY: Başvuru Sonucu Alınan API-KEY
APIKEY Authorization: Kullanıcı Girişi Oturum Alma işleminden dönen Hash değeri
Checker: Her istek için oluşturulan imzadır.
 

İstek Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
id	String	Emrin ID’ si
price	String	Düzeltilecek Fiyat
lot	String	Lot miktarı( Viop emri ise girilmelidir.)
viop	String	Emrin viop olduğunu belirtir(Viop ise true olmalıdır)
subAccount	String	Alt Hesap Numarası (Boş gönderilebilir. Boş gönderilirse Aktif Hesap Bilgilerini Getirir.)
Örnek Body

{
   "id": "001VEV",
   "price": "2.04",
   "lot": "0",
   "viop": false,
   "Subaccount": ""
}

 

Sonuç Parametreleri

Parametre Adı	Parametre Tipi	Açıklama
message	String	Emrin iletimi hakkında bilgi verir.
duration	String	-
Örnek Response

{
   "success": true,
   "message": "IYILESOK",
   "content": {
      "message": "IYILESOK",
      "duration": "-"
   }
}

Websocket Protokolü (WSS)
Canlı veya gecikmeli olarak veri görüntülemenizi sağlar.

 

HeartBeat Atma

Aşağıdaki şekilde Json String gönderilir. Websocket bağlantısının devam edebilmesi için düzenli aralıklarla HeartBeat gönderimi yapılması gerekmektedir.

Type = H olmalıdır 
Token değeri = Authorization
Örnek Request Body

{
  "Type": "H",
  "Token": "eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1 NiIsInR5 cCI6IkpXVCJ9.eyJBdXRob3JpemF0aW9uIjoiQXV0aG9yaXplZCIsIkN1c3RvbWVyTm8iOiIxMzQ1MTcyMCIsIk5ld3NsZXR0 ZXIiOiJU cnVlIiwiSXNCbG9ja2VkIjoiRmFsc2UiLCJFbWFpbCI6IjEzNDUxNzIwIiwiVXNlcklkIjoiMTAxIiwiRGVuaXpiYW5rIjoiVHJ1ZSIsI m5iZiI6MTY1MzkyMDg2NiwiZXhwIjoxNjU0MDA3MjY2fQ.kzkSYQOnkA9Qn8qTiV_Fq8IvqXKsQ3m-QuMv6Kjqkdw"
}

 

T Paketi Abone Olma

Aşağıdaki şekilde Json String gönderilir.

Type = T olmalıdır
Token değeri = Authorization
Symbols = List()
Symbols yerine T paketinde gelmesi istenilen semboller liste şeklinde yazılır. Bütün Sembollerin gelmesi için "ALL" yazılması gerekmektedir.

Örnek Request Body

{
  "Type": "T",
  "Token": "eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1 NiIsInR5 cCI6IkpXVCJ9.eyJBdXRob3JpemF0aW9uIjoiQXV0aG9yaXplZCIsIkN1c3RvbWVyTm8iOiIxMzQ1MTcyMCIsIk5ld3NsZXR0 ZXIiOiJU cnVlIiwiSXNCbG9ja2VkIjoiRmFsc2UiLCJFbWFpbCI6IjEzNDUxNzIwIiwiVXNlcklkIjoiMTAxIiwiRGVuaXpiYW5rIjoiVHJ1ZSIsI m5iZiI6MTY1MzkyMDg2NiwiZXhwIjoxNjU0MDA3MjY2fQ.kzkSYQOnkA9Qn8qTiV_Fq8IvqXKsQ3mQuMv6Kjqkdw",
  "Symbols": [
    "GARAN",
    "TSKB"
  ]
}

 

D Paketi Abone Olma

Aşağıdaki şekilde Json String gönderilir.

Type = D olmalıdır
Token değeri = Authorization
Symbols = List()
Symbols yerine D paketinde gelmesi istenilen semboller liste şeklinde yazılır. Bütün Sembollerin gelmesi için "ALL" yazılması gerekmektedir.

Örnek Request Body

{
  "Type": "D",
  "Token": "eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1 NiIsInR5 cCI6IkpXVCJ9.eyJBdXRob3JpemF0aW9uIjoiQXV0aG9yaXplZCIsIkN1c3RvbWVyTm8iOiIxMzQ1MTcyMCIsIk5ld3NsZXR0 ZXIiOiJU cnVlIiwiSXNCbG9ja2VkIjoiRmFsc2UiLCJFbWFpbCI6IjEzNDUxNzIwIiwiVXNlcklkIjoiMTAxIiwiRGVuaXpiYW5rIjoiVHJ1ZSIsI m5iZiI6MTY1MzkyMDg2NiwiZXhwIjoxNjU0MDA3MjY2fQ.kzkSYQOnkA9Qn8qTiV_Fq8IvqXKsQ3mQuMv6Kjqkdw",
  "Symbols": [
    "GARAN"
  ]
}

 

Örnek "T" Tipindeki Response

{

   "Type":"T",

   "Content":{

      "Symbol":"PEHOL",

      "Market":"IMKBH",

      "Price":2.48,

      "Change":-0.27,

      "Ask":2.48,

      "Bid":0.0,

      "Date":"2024-09-25T14:46:35+03:00",

      "ChangePercentage":-9.82,

      "High":2.48,

      "Low":2.48,

      "TradeQuantity":100.0,

      "Direction":"B",

      "RefPrice":2.75,

      "BalancePrice":0.0,

      "BalanceAmount":0.0,

      "Buying":"Midas",

      "Selling":"Seker"

   }

}

 

Örnek "D" Tipindeki Response

{
   "Type":"D",
   "Content":{
      "Symbol":"ESEN",
      "Market":"IMKBH",
      "Direction":"B",
      "Row":0,
      "Quantity":8348,
      "Price":20.04,
      "OrderCount":128,
      "Date":"2024-09-25T14:51:18+03:00"
   }
}

Örnek "O" Tipindeki Response

{

   "Type":"O",

   "Content":{

      "Id":"fe52938525764d6c81aa305444e5937f",

      "Date":"2024-09-25T15:30:25.61",

      "Direction":1,

      "Symbol":"TSKB",

      "Lot":1.0,

      "PriceType":0,

      "Price":11.78,

      "Comment":"Referans Numaranız: FO7XEA;20240925FO7XEA - HISSEOK ",

      "Status":2,

      "Channel":"DenizYatirimHcp",

      "ExecutedLot":1.0,

      "ExecutedPrice":11.77

   }

}
