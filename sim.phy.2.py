# malzeme_tasima_simulasyon_nihai.py

import simpy
import random
import math
import statistics

# -------------------------------------------------
# ZAMAN VE TOHUM
# -------------------------------------------------
HAFTA_SURESI_SN = 144000   # 1 hafta (40 saat)
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
# EKİPMAN HIZLARI
# -------------------------------------------------
ekipman_hizlari = {
    "forklift": 1.0,
    "transpalet": 0.6
}

# -------------------------------------------------
# MALİYET PARAMETRELERİ (RAPORDAKİ DEĞERLER)
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
def crf(i, n):
    return (i * (1 + i) ** n) / ((1 + i) ** n - 1)

def sefer_bilesenleri(toplam, mesafe, hiz):
    yol = mesafe / hiz
    kalan = max(0, toplam - yol)
    return yol, kalan / 2, kalan / 2

# -------------------------------------------------
# SİMÜLASYON
# -------------------------------------------------
def simulasyonu_calistir(forklift_sayisi, transpalet_sayisi, talep_carpani):

    env = simpy.Environment()

    forklift = simpy.Resource(env, capacity=forklift_sayisi)
    transpalet = simpy.Resource(env, capacity=transpalet_sayisi)

    bekleme = {r: [] for r in rotalar}
    hizmet = {r: [] for r in rotalar}
    tamamlanan = {r: 0 for r in rotalar}
    calisma = {"forklift": 0.0, "transpalet": 0.0}

    def sefer(env, rota_adi, rota):
        ekipman = rota["ekipman"]
        kaynak = forklift if ekipman == "forklift" else transpalet

        yol, yukleme, bosaltma = sefer_bilesenleri(
            rota["sefer_suresi"],
            rota["mesafe"],
            ekipman_hizlari[ekipman]
        )

        talep_zamani = env.now
        with kaynak.request() as req:
            yield req
            bekleme[rota_adi].append(env.now - talep_zamani)

            basla = env.now
            yield env.timeout(yukleme)
            yield env.timeout(yol)
            yield env.timeout(bosaltma)

            sure = env.now - basla
            hizmet[rota_adi].append(sure)
            calisma[ekipman] += sure
            tamamlanan[rota_adi] += 1

    def rota_uret(env, rota_adi, rota):
        haftalik = rota["haftalik_sefer"] * talep_carpani
        ortalama = HAFTA_SURESI_SN / haftalik
        while env.now < HAFTA_SURESI_SN:
            yield env.timeout(random.expovariate(1 / ortalama))
            env.process(sefer(env, rota_adi, rota))

    for r in rotalar:
        env.process(rota_uret(env, r, rotalar[r]))

    env.run(until=HAFTA_SURESI_SN)

    # -------------------------------------------------
    # PERFORMANS
    # -------------------------------------------------
    forklift_util = calisma["forklift"] / (HAFTA_SURESI_SN * forklift_sayisi)
    transpalet_util = calisma["transpalet"] / (HAFTA_SURESI_SN * transpalet_sayisi)

    # -------------------------------------------------
    # MALİYET
    # -------------------------------------------------
    hurda_bugunku = hurda_degeri / ((1 + yillik_faiz) ** 7)
    efektif_yatirim = forklift_yatirim - hurda_bugunku
    aylik_crf = crf(aylik_faiz, ekonomik_omur_ay)

    sabit_forklift = efektif_yatirim * aylik_crf * forklift_sayisi
    sabit_transpalet = transpalet_yatirim * aylik_crf * transpalet_sayisi

    aylik_bakim = yillik_bakim / 12
    operator_maliyeti = operator_maasi * forklift_util

    toplam_maliyet = (
        sabit_forklift +
        sabit_transpalet +
        aylik_bakim +
        operator_maliyeti
    )

    return {
        "Tamamlanan Sefer": tamamlanan,
        "Ort. Bekleme (sn)": {r: statistics.mean(bekleme[r]) for r in rotalar},
        "Forklift Util (%)": forklift_util * 100,
        "Transpalet Util (%)": transpalet_util * 100,
        "Aylık Toplam Maliyet (TL)": toplam_maliyet
    }

# -------------------------------------------------
# SENARYOLAR
# -------------------------------------------------
if __name__ == "__main__":

    print("\n=== BAZ SENARYO ===")
    print(simulasyonu_calistir(1, 1, 1.0))

    print("\n=== ARA SENARYO (%30 TALEP + 2 FORKLIFT) ===")
    print(simulasyonu_calistir(2, 1, 1.3))

    print("\n=== STRES SENARYOSU (%50 TALEP + 2 FORKLIFT + 2 TRANSPALET) ===")
    print(simulasyonu_calistir(2, 2, 1.5))