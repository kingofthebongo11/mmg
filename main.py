from grunt_class import PermafrostSoil, SoilType
from borehole_class import Borehole
from II_calculations import disp_calculation
def main():
    #Задаем глубину оттаивания грунтов
    Hc = 8 #м
    #Задаем нагрузку на фундамент
    F = 6821 #кН
    #Задаем габариты фундаментой плиты
    a = 10#м
    b = 1.9#м
    #Задаем отметку фундаментной плиты
    H=98#м

    mmg1 = PermafrostSoil(
        code="L1",
        name="Loam",
        soil_type=SoilType.SAND_AND_SUPES,
        rho=1700,
        Ath=0.01,
        mth=0.0000306
    )
    mmg2 = PermafrostSoil(
        code="L2",
        name="Loam",
        soil_type=SoilType.LOAM,
        rho=1800,
        Ath=0.016,
        mth=0.000051
    )

    bh = Borehole(code="BH-01", z_top=100)
    bh.add(mmg1, 5)  # чейнинг: добавили 3 слоя
    bh.add(mmg2, 10)  # чейнинг: добавили 3 слоя
    s = disp_calculation(borehole=bh,Hc=Hc, H=H, F=F, a=a, b=b)
    print(s)

if __name__ == '__main__':
    main()


