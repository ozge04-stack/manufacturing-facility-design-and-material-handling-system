# malzeme_tasima_simulasyon_maliyet.py

import simpy
import random
import math

# -------------------------------------------------
# ZAMAN VE TOHUM
# -------------------------------------------------
HAFTA_SURESI_SN = 144000   # 1 hafta (sn)
random.seed(42)

# -------------------------------------------------
# ROTA VERİLERİ (TABLO 15.1)
# -------------------------------------------------
rotalar = {
    "D1_H1": {"haftalik_sefer": 6,  "mesafe": 7.5,  "ekipman": "forklift",   "sefer_suresi": 900},
    "D1_M":  {"haftalik_sefer": 3,  "mesafe": 17.5, "ekipman": "transpalet", "sefer_suresi": 600},
    "H1_H2": {"haftalik_sefer": 12, "mesafe": 7.5,  "ekipman": "transpalet", "sefer_suresi": 600},
    "M_D2":  {"haftalik_sefer": 12, "mesafe": 7.5,  "ekipman": "forklift",   "sefer_suresi": 900},
}

# -------------------------------------------------
# EKİPMAN HIZLARI (OPTİMAL KABUL)
# -------------------------------------------------
ekipman_hizlari = {
    "forklift": 1.0,      # m/s
    "transpalet": 0.6     # m/s
}

# -------------------------------------------------
# MALİYET PARAMETRELERİ (KAYNAĞINDAN)
# -------------------------------------------------
forklift_yatirim = 1_000_000
transpalet_yatirim = 10_000
hurda_degeri = 50_000

yillik_faiz = 0.15
aylik_faiz = 0.0125
ekonomik_omur_ay = 84

yillik_bakim = 20_000
operator_maasi = 30_000

# -------------------------------------------------
# YARDIMCI FONKSİYONLAR
# -------------------------------------------------
def sermaye_geri_kazanim_faktoru(i, n):
    return (i * (1 + i) ** n) / ((1 + i) ** n - 1)

def sefer_sure_bilesenleri(toplam_sure, mesafe, hiz):
    yol_suresi = mesafe / hiz
    kalan = max(0, toplam_sure - yol_suresi)
    yukleme = kalan / 2
    bosaltma = kalan / 2
    return yol_suresi, yukleme, bosaltma

# -------------------------------------------------
# SİMÜLASYON FONKSİYONU
# -------------------------------------------------
def simulasyonu_calistir(forklift_sayisi, transpalet_sayisi, talep_carpani):

    ortam = simpy.Environment()

    forklift = simpy.Resource(ortam, capacity=forklift_sayisi)
    transpalet = simpy.Resource(ortam, capacity=transpalet_sayisi)

    bekleme_sureleri = {r: [] for r in rotalar}
    hizmet_sureleri = {r: [] for r in rotalar}
    tamamlanan_sefer = {r: 0 for r in rotalar}

    ekipman_calisma_suresi = {"forklift": 0.0, "transpalet": 0.0}

    def sefer(ortam, rota_adi, rota):
        ekipman = rota["ekipman"]
        kaynak = forklift if ekipman == "forklift" else transpalet

        yol, yukleme, bosaltma = sefer_sure_bilesenleri(
            rota["sefer_suresi"],
            rota["mesafe"],
            ekipman_hizlari[ekipman]
        )

        talep_zamani = ortam.now
        with kaynak.request() as istek:
            yield istek
            bekleme_sureleri[rota_adi].append(ortam.now - talep_zamani)

            baslangic = ortam.now
            yield ortam.timeout(yukleme)
            yield ortam.timeout(yol)
            yield ortam.timeout(bosaltma)

            sure = ortam.now - baslangic
            hizmet_sureleri[rota_adi].append(sure)
            ekipman_calisma_suresi[ekipman] += sure
            tamamlanan_sefer[rota_adi] += 1

    def rota_uret(ortam, rota_adi, rota):
        haftalik_sefer = rota["haftalik_sefer"] * talep_carpani
        ortalama_aralik = HAFTA_SURESI_SN / haftalik_sefer

        while ortam.now < HAFTA_SURESI_SN:
            yield ortam.timeout(random.expovariate(1 / ortalama_aralik))
            ortam.process(sefer(ortam, rota_adi, rota))

    for rota_adi, rota in rotalar.items():
        ortam.process(rota_uret(ortam, rota_adi, rota))

    ortam.run(until=HAFTA_SURESI_SN)

    # -------------------------------------------------
    # PERFORMANS HESAPLARI
    # -------------------------------------------------
    forklift_utilizasyon = ekipman_calisma_suresi["forklift"] / HAFTA_SURESI_SN
    transpalet_utilizasyon = ekipman_calisma_suresi["transpalet"] / HAFTA_SURESI_SN

    # -------------------------------------------------
    # MALİYET HESAPLARI
    # -------------------------------------------------
    hurda_bugunku = hurda_degeri / ((1 + yillik_faiz) ** 7)
    efektif_yatirim = forklift_yatirim - hurda_bugunku

    crf = sermaye_geri_kazanim_faktoru(aylik_faiz, ekonomik_omur_ay)

    sabit_forklift = efektif_yatirim * crf * forklift_sayisi
    sabit_transpalet = transpalet_yatirim * crf * transpalet_sayisi

    aylik_bakim = yillik_bakim / 12
    operator_maliyeti = operator_maasi * forklift_utilizasyon

    toplam_aylik_maliyet = (
        sabit_forklift +
        sabit_transpalet +
        aylik_bakim +
        operator_maliyeti
    )

    return {
        "Forklift Utilizasyon (%)": forklift_utilizasyon * 100,
        "Transpalet Utilizasyon (%)": transpalet_utilizasyon * 100,
        "Toplam Aylık Maliyet (TL)": toplam_aylik_maliyet
    }

# -------------------------------------------------
# SENARYOLAR
# -------------------------------------------------
if __name__ == "__main__":

    print("=== BAZ SENARYO ===")
    baz = simulasyonu_calistir(
        forklift_sayisi=1,
        transpalet_sayisi=1,
        talep_carpani=1.0
    )
    print(baz)

    print("\n=== STRES SENARYOSU ===")
    stres = simulasyonu_calistir(
        forklift_sayisi=2,
        transpalet_sayisi=2,
        talep_carpani=1.5
    )
    print(stres)
