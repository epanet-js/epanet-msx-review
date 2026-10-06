# Published reaction models

[All changes](../README.md) · [Benchmark cases](README.md)

The main cases run the reaction systems of the EPANET-MSX manual. The cases on this page test the patches on more complex chemistry, taken from published papers, and on paths of MSX that the original cases do not use: wall species driven by the wall shear stress, rates switched on and off by dozens of `STEP()` terms, timed `MASS` sources with a pattern, a temperature species that sets the rates of the other species, up to 20 species in every pipe, and stiff kinetics. Each file is a new implementation of the published equations, written for this repository. The papers are cited in the files and below; no text or listing is copied from them.

**InfoWater.** InfoWater MSX ships with built-in example models named CHLORAMINE, DBP, INACTIVATION, PSM1, PSM2, Temperature and Turbidity. Their formulations are given only in InfoWater's user guide, which is not public. Only CHLORAMINE could be matched: its rate constants and terms are those of the manual's monochloramine model (Listing 5.5), which `net3-chlm` and several other cases here already run. The files on this page replicate the other kinds from the open literature: DBP (two files), PSM, Temperature, INACTIVATION, and Turbidity (PODDS and VCDM). They correspond to InfoWater's models in purpose only, not in coefficients; everything in them comes from the papers cited.

## The models

| Model | File | Species and terms | Solver, step | What it exercises | Unpatched, 1 thread |
|---|---|---|---|---|---:|
| [Disinfection by-products](#disinfection-by-products-dbp) (Fisher 2023) | `ltown-dbp.msx` | 5 bulk; 22 terms | RK5, 300 s | Deeply nested `[TERMS]`; a Sherwood number from `Ff`, with laminar and turbulent branches | ~33 s |
| [Bacterial regrowth with THM](#bacterial-regrowth-with-thm) (Abhijith et al. 2021) | `ltown-regrowth-thm.msx` | 5 bulk, 1 wall; 23 terms | RK5, 300 s | Bacteria exchanged between water and wall through the shear stress; values from 10<sup>−3</sup> to 10<sup>3</sup>, with tolerances per species | ~82 s |
| [Two-reactant chlorine, two waters](#two-reactant-chlorine-with-two-source-waters-psm) (Kastl et al. 1999; Fisher et al.) | `ltown-psm.msx` | 7 bulk; 25 terms | RK5, 300 s | Two waters that blend and keep their own kinetics; a friction factor computed in `[TERMS]` | ~128 s |
| [Water temperature](#water-temperature) (Blokker et al. 2024) | `ltown-temperature.msx` | 6 bulk; 27 terms | RK5, 300 s | A temperature species that drives every other rate | ~121 s |
| [Intrusion and inactivation](#intrusion-and-inactivation) (USEPA 2020; Helbling and VanBriesen) | `ltown-inactivation.msx` | 10 bulk, 1 formula; 9 terms | ROS2, 300 s | Stiff kinetics; six `MASS` sources switched on by a pattern | ~97 s |
| [PODDS](#podds-discolouration) (Boxall and Saul 2005) | `ltown-podds.msx` | 1 bulk, 1 wall, 2 wall formulas; 7 terms | RK5, 60 s | A wall species driven by the shear stress (`U`, `Ff`) that erodes or regenerates by `STEP()`; an initial wall state per pipe | ~136 s |
| [VCDM](#vcdm-discolouration) (Furnass et al. 2014) | `ltown-vcdm.msx` | 1 bulk, 17 wall, 2 wall formulas; 37 terms | Euler, 60 s | 20 species in every pipe, 68 `STEP()` switches, about 1,800 `LINK` lines of initial values | ~187 s |

The times are of 85a303d, unpatched, on L-Town 24 h (905 pipes, 5-minute hydraulic steps), on one thread of an Apple M1 Pro with other work running, so they are approximate. L-Town is in SI units, so D and Len are in metres throughout. `--cases literature` runs these seven and a dispersion case on BWSN2, and `--cases literature-large` runs the seven on two larger networks ([On other networks](#on-other-networks)); the results are in the [main README](../README.md#published-reaction-models).

## Disinfection by-products (DBP)

`ltown-dbp.msx` models chlorine decay by the augmented two-reactant model (2RA): fast and slow reducing agents, F and S, each react second-order with chlorine, with an Arrhenius factor for temperature. In pipes chlorine also reacts at the wall, at a rate limited by both biofilm activity and mass transfer (the EXPBIO wall model, with the rough-pipe mass transfer of EXBRUF). THM and HAA form in proportion to the chlorine consumed in the bulk. Fisher (2023) published the model as MSX listings, calibrated on a pipeline in Perth (Mirrabooka).

**Sources**

- Fisher, I.H. (2023). Integrated EPANET-MSX process models of chlorine and its by-products in drinking water distribution systems. *Water Environment Research* 95(12):e10949. [doi:10.1002/wer.10949](https://doi.org/10.1002/wer.10949). Open access (CC BY-NC 4.0). The equations of Table 2 and the listings of Tables 4 to 6.
- Cited there and not consulted here, all subscription: the 2RA model, Fisher, I., Kastl, G. and Sathasivan, A. (2012), *Water Research* 46(10):3293-3303, [doi:10.1016/j.watres.2012.03.017](https://doi.org/10.1016/j.watres.2012.03.017); the wall model, Fisher, I., Kastl, G. and Sathasivan, A. (2017), *Water Research* 125:427-437, [doi:10.1016/j.watres.2017.08.066](https://doi.org/10.1016/j.watres.2017.08.066); the THM and HAA yields, Sathasivan et al. (2020), *Water Research* 184:116189, and Premarathna et al. (2022), *Science of the Total Environment* 857:159267.

**Equations** (t in hours; concentrations in mg/L, F and S in mg Cl-equivalent/L):

```
dF/dt   = -kF*θ*F*CL                θ = exp(E/R*(T - 20)/(293*(T + 273)))
dS/dt   = -kS*θ*S*CL
dCL/dt  = dF/dt + dS/dt + (4/D)*Rw  pipes, D in dm; tanks: bulk terms only
Rw      = -BA*CL/(1 + BA/KM)        BA = ABF20*θ*exp(-BBF*CL), KM = Sh*DCL/D
Sh      = (Ff/8)(Re - 1000)Sc/(1 + 12.7(Ff/8)^0.5 (Sc^0.66 - 1))   Re > 2300 (Gnielinski)
        = 3.65 + 0.0668*Gz/(1 + 0.04*Gz^(2/3)), Gz = D*Re*Sc/Len    Re < 2300
dTHM/dt = -KTHM*(dF/dt + dS/dt),   dHAA/dt = -KHAA*(dF/dt + dS/dt)
```

Sc = ν/DCL, with ν = exp(-3.7188 + 578.92/(T + 135.56))·10<sup>−6</sup> m²/s and DCL = (0.0365·T + 0.5176)·10<sup>−9</sup> m²/s (Fisher's equations 11 and 12).

| Coefficient | Value | From |
|---|---|---|
| kF, kS at 20 °C | 0.0054, 0.0017 L/mg/h | Fisher (2023), Table 4 |
| E/R | 1300 K | Table 4 |
| Water temperature T | 22.6 °C | Table 4 |
| KTHM, KHAA | 0.043, 0.020 mg per mg of chlorine | Table 4, the defaults of the yield papers |
| ABF20, BBF | 1000 dm/h, 26 L/mg | Tables 5 and 6 |
| F, S at the reservoirs | 4.1, 49.9 mg Cl-eq/L | Table 4 |
| Chlorine at the reservoirs | 1.2 mg/L | Chosen here |
| RTOL, ATOL | 0.001, 0.0001 | Table 4 |

**Deviations and assumptions**

- **A laminar branch.** Gnielinski's correlation is negative below Re = 1000, and most of L-Town's pipes are laminar for much of the day, so below Re = 2300 the file uses the laminar Sherwood number of the manual's Listing 5.2. Fisher validated the model on a turbulent trunk main.
- **By-products from bulk consumption only**, as Fisher's equation 16 defines them; his listings, joined literally, would count the chlorine consumed at the wall too.
- **Viscosity.** MSX's Re uses a fixed viscosity of about 20 °C (1.1·10<sup>−5</sup> ft²/s), whatever the network file says, while Sc uses ν at 22.6 °C. The temperature terms, which Fisher computes once, are evaluated every time.
- **Sources and start.** Both reservoirs supply the same water, dosed to 1.2 mg/L rather than 0.4 to 0.76 mg/L, because L-Town's residence times reach 17 to 24 hours against about 6 on the pipeline. The network starts with partly reacted water (0.3 mg/L of chlorine). The step is 300 s, L-Town's hydraulic step, instead of 360 s.

**On L-Town 24 h** chlorine ranges from 1.2 mg/L at the reservoirs to 0.005 mg/L. At 24 h the median over the network is 0.96 mg/L and the 5th percentile 0.09 mg/L, against 0.19 mg/L without the wall reaction, which takes over below about 0.3 mg/L. THM reach about 0.04 mg/L and HAA 0.02 mg/L in the oldest water.

## Bacterial regrowth with THM

`ltown-regrowth-thm.msx` follows Abhijith, Kadinski and Ostfeld (2021), who ran their model in EPANET-MSX: chlorine, total and biodegradable organic carbon (TOC, BDOC), bacteria suspended in the water and attached to the wall, and THM. Chlorine is consumed by organic matter and by bacteria, and decays at the wall. Bacteria grow on BDOC, inhibited by chlorine; they die, deposit on the wall and are detached from it by the shear stress. THM form from both chlorine reactions.

**Source**

- Abhijith, G.R., Kadinski, L. and Ostfeld, A. (2021). Modeling bacterial regrowth and trihalomethane formation in water distribution systems. *Water* 13(4):463. [doi:10.3390/w13040463](https://doi.org/10.3390/w13040463). Open access (CC BY 4.0). Equations 1 to 6, the base values of Table 1 and the source waters of Test Problem 2.

**Equations** (t in s; C chlorine, N TOC, S BDOC in mg/L; Xb in CFU/mL, X' = 1000·Xb per litre; Xa in CFU/cm²; H THM in µg/L):

```
dC/dt  = -kCN*N*C - kCX*X'*C - kw*kf/((kw + kf)*Rh)*C
dN/dt  = -G/Y - YN*kCN*N*C + a*cc*(YX*kCX*X'*C + kmort*Xb)
dS/dt  = -G/Y - YN*kCN*S*C + a*cc*(YX*kCX*X'*C + kmort*Xb)
dXb/dt = G - YX*kCX*X'*C - kmort*Xb - kdep*Xb + kdet*τw*Xa/Rh
dXa/dt = µa*exp(-kinact*C/kr)*fT*Xa - kmort*Xa + kdep*Xb*Rh - kdet*τw*Xa
dH/dt  = YH1*kCN*N*C + YH2*kCX*X'*C
G   = µb*S/(Ks + S)*exp(-kinact*C)*fT*Xb,  fT = exp(-((Topt - T)/(Topt - Ti))^2)
kCN = 3e4*exp(-6050/(T + 273)),            kCX = 3e-4*exp(-6050/(T + 273))
τw  = ρ*f*U^2/8,                           f = 0.316*Re^-0.25 (Blasius)
kf  = Sh*Dm/D (EPANET's correlations),     Rh = D/4 (in cm in the exchange terms)
```

Tanks have the bulk terms only: no wall decay, deposition or detachment.

| Coefficient | Value | From |
|---|---|---|
| kw | 1.04e-7 m/s | Table 1 |
| µb, µa | 4.2e-4, 8.6e-7 1/s | Table 1 |
| Ks | 0.195 mg-C/L | Table 1 |
| Y, YX | 7,000 and 3.4e5 (CFU/mL) per mg/L | Table 1, in the units below |
| YN | 0.98 mg-C per mg of chlorine | Table 1 |
| kinact, kr | 0.35 L/mg, 100 | Table 1 |
| kmort = kdep, kdet | 6.3e-5 1/s, 6.618e-7 m·s/g | Table 1 |
| a | 0.3 | Table 1 |
| YH1, YH2 | 118.435, 4.487 µg per mg of chlorine | Table 1 |
| Topt, Ti, T | 37, 7, 25 °C | Table 1; T as in the paper |
| cc, Dm, ρ | 1e-6 (mg-C/L) per (CFU/mL); 1.21e-9 m²/s; 997,050 g/m³ | Added here: 10<sup>−9</sup> mg of carbon per cell, EPANET's default diffusivity, water at 25 °C |

**Deviations and assumptions**

- **Units.** Table 1 mixes per-millilitre and per-litre units. The file takes the reading that is dimensionally consistent and also reproduces the paper's sensitivity results: yields per mg/L at 10<sup>−9</sup> mg of carbon per cell, kCX (L/CFU/s) applied to the count per litre, and dead cells converted to carbon by cc. Without the last two, chlorine would barely kill bacteria, and the `a` term would add several mg/L of carbon an hour.
- **Two misprints corrected**: the missing C after kCN·N in equation 2, and the temperature factor printed as exp[(−x)²], which would speed growth away from the optimum.
- **Formulas the paper does not give**: EPANET's Sherwood correlations for kf and a standard Vogel fit for the viscosity at 25 °C. Blasius applies at every Re, laminar included, as the paper says.
- **Sources and start.** R1 supplies the water of scenario 2b (1.0 mg/L of chlorine, 2.0 mg/L of TOC), R2 that of scenario 2a (0.5 and 1.0), with BDOC at 30 % of TOC and 0.001 CFU/mL. The network starts with partly reacted water (60 µg/L of THM) and runs for 24 hours; the paper ran to a steady state.

**On L-Town 24 h** chlorine falls to 0.01 to 0.13 mg/L at the far nodes and the tank, where BDOC is nearly used up and suspended bacteria reach 70 to 710 CFU/mL from 12 h on; the paper reports 5.3 to 1.4·10<sup>4</sup> CFU/mL across its scenarios. THM reach 111 µg/L, high because YH1 credits 118 µg of THM to each mg of chlorine consumed by organic matter.

## Two-reactant chlorine with two source waters (PSM)

`ltown-psm.msx` is the parallel second-order, or two-reactant (2R), model of chlorine decay, with two source waters. Each reservoir's water brings its own fast and slow reducing agents (FA and SA from R1, FB and SB from R2), which keep their own rate coefficients in a blend, and all four react with one chlorine pool, as in Fisher et al. (2015). The wall reaction and by-products are those of the [DBP model](#disinfection-by-products-dbp). Nothing public says what distinguishes InfoWater's PSM1 from PSM2; "parallel second-order" is how the literature names the two-reactant model, and that is the reading used here.

**Sources**

- Kastl, G., Fisher, I. and Jegatheesan, V. (1999). Evaluation of chlorine decay kinetics expressions for drinking water distribution systems modelling. *Journal of Water Supply: Research and Technology - AQUA* 48(6):219-226. [doi:10.2166/aqua.1999.0024](https://doi.org/10.2166/aqua.1999.0024). Subscription; not consulted (the origin of the 2R model).
- Fisher, I., Kastl, G. and Sathasivan, A. (2011). Evaluation of suitable chlorine bulk-decay models for water distribution systems. *Water Research* 45(16):4896-4908. [doi:10.1016/j.watres.2011.06.032](https://doi.org/10.1016/j.watres.2011.06.032). Subscription; not consulted.
- Fisher, I., Kastl, G. and Sathasivan, A. (2012). A suitable model of combined effects of temperature and initial condition on chlorine bulk decay in water distribution systems. *Water Research* 46(10):3293-3303. [doi:10.1016/j.watres.2012.03.017](https://doi.org/10.1016/j.watres.2012.03.017). Subscription; the abstract and introduction, for the 2R equations and units.
- Fisher, I., Kastl, G., Sathasivan, A., Cook, D. and Seneverathne, L. (2015). General model of chlorine decay in blends of surface waters, desalinated water, and groundwaters. *Journal of Environmental Engineering* 141. [doi:10.1061/(ASCE)EE.1943-7870.0000980](https://doi.org/10.1061/(ASCE)EE.1943-7870.0000980). Subscription; as summarised in Fisher (2023).
- Fisher, I. (2022). A multi-species decay model to support cost-effective chlorination in distribution systems. Bentley Virtuosity blog, 24 March 2022. [blog.virtuosity.com](https://blog.virtuosity.com/hydraulics-hydrology/a-multi-species-decay-model-to-support-cost-effective-chlorination-in-distribution-systems). Free to read. The coefficients of Greenvale water.
- Fisher (2023), as in the DBP model, open access: the Mirrabooka coefficients, the wall model, ν(T), DCL(T) and the yields. Its wall model also appears in Fisher, I., Kastl, G. and Sathasivan, A. (2023), Validity of chlorine-wall reaction models for drinking water distribution systems, *Urban Water Journal* 20(9):1157-1168, [doi:10.1080/1573062X.2023.2241437](https://doi.org/10.1080/1573062X.2023.2241437), open access (CC BY-NC-ND), which could not be obtained.

**Equations** (as the DBP model, except):

```
dFi/dt  = -kFi*θi*Fi*CL,  dSi/dt = -kSi*θi*Si*CL     i = A (R1 water), B (R2 water)
dCL/dt  = Σi (dFi/dt + dSi/dt) + (4/D)*Rw           tanks: bulk terms only
BA      = ABF20*θW*exp(-BBF*CL)
f       = 0.25/[log10(0.27*ε/D + 5.74/Re*^0.9)]^2   Swamee-Jain, Re* = max(Re, 2300), in Gnielinski's Sh
dTHM/dt = -KTHM*dCL/dt,   dHAA/dt = -KHAA*dCL/dt    dCL/dt with the wall term
```

The water is at a fixed 20 °C, so every θ is 1.

| Coefficient | Value | From |
|---|---|---|
| Water A (R1), Greenvale: kF, kS at 20 °C; E/R | 0.164, 0.00496 L/mg/h; 10,500 K | Fisher (2022) |
| Water A: F, S at R1 | 1.13, 2.87 mg Cl-eq/L | Fisher (2022) |
| Water B (R2), Mirrabooka: kF, kS at 20 °C; E/R | 0.0054, 0.0017 L/mg/h; 1,300 K | Fisher (2023), Table 4 |
| Water B: F, S at R2 | 4.1, 49.9 mg Cl-eq/L | Table 4 |
| ABF20, BBF; E/R at the wall | 1000 dm/h, 26 L/mg; 5,000 K | Tables 5 and 6; the paper's typical value |
| Roughness ε | 2.5 mm | Table 6 |
| KTHM, KHAA | 0.043, 0.020 | Table 4 |
| T; chlorine at both reservoirs | 20 °C; 1.0 mg/L | Chosen here |

**Deviations and assumptions**

- **A Swamee-Jain friction factor**, with a fixed roughness, instead of `Ff`, which is not finite at zero flow. Fisher's Table 6 has Swamee-Jain commented out, with a natural logarithm, Re<sup>0.9</sup> multiplying and a squared logarithm that MSX would evaluate as 0; the file uses log10, squares by multiplication, and holds Re at 2300 or more inside the turbulent branch so that it stays finite. The laminar branch is as in the DBP model.
- **ε = 2.5 mm** is Fisher's value for an old cement-lined main; L-Town's Hazen-Williams coefficients (120 to 140) suggest smoother pipes.
- **Two waters from different systems**, Greenvale (a fast initial demand) and Mirrabooka (a nearly first-order one), paired for the benchmark.
- **By-products from total consumption**, wall included, as in Fisher's listing; the DBP file follows his equation 16 instead.
- **Start.** The network starts with a 50/50 blend of the two waters after 6 hours of bulk reaction.

**On L-Town 24 h** chlorine ranges from 1.0 to 0.007 mg/L. Most of the water is young (median age 2 hours), so at 24 h the junctions fed by the reservoirs have a median of 0.79 mg/L and a 5th percentile of 0.51 mg/L. About 96 of the 785 nodes still hold the initial water after 24 hours; chlorine there falls to about 0.01 mg/L, as the wall reaction speeds up below about 0.3 mg/L. THM reach 0.043 mg/L and HAA 0.020 mg/L.

## Water temperature

`ltown-temperature.msx` carries the water temperature TW as a bulk species that exchanges heat with the soil around each pipe, by the WTM+ model of Blokker, Pan and van Laarhoven (2024): heat passes through the water's boundary layer, the pipe wall and a "thermal sphere of influence" of soil. The temperature drives the 2RA chlorine model of one water (Greenvale) with the wall reaction and by-products of the [PSM model](#two-reactant-chlorine-with-two-source-waters-psm): the Arrhenius factors, viscosity, chlorine diffusivity and biofilm activity are all evaluated at TW.

**Sources**

- Blokker, M., Pan, Q. and van Laarhoven, K. (2024). Validation of an enhanced drinking water temperature model during distribution. *Water* 16(19):2796. [doi:10.3390/w16192796](https://doi.org/10.3390/w16192796). Open access (CC BY). Equations 1 and 2, the Nusselt numbers, the property values of Tables A2 and A8, and the recommended spheres of influence.
- Blokker, E.J.M. and Pieterse-Quirijns, E.J. (2013). Modeling temperature in the drinking water distribution system. *Journal AWWA* 105(1):E19-E28. [doi:10.5942/jawwa.2013.105.0011](https://doi.org/10.5942/jawwa.2013.105.0011). Subscription; not consulted. The original model, the case without a sphere of influence, as restated in Blokker et al. (2024).
- Cincotta, C., Blokker, M., Bragalli, C. and Kapelan, Z. (2024). Spatial analysis of water temperature in a drinking water distribution system for climate change adaptation. *Engineering Proceedings* 69:127. [doi:10.3390/engproc2024069127](https://doi.org/10.3390/engproc2024069127). Open access (CC BY). The model run in EPANET-MSX, with the soil temperature a constant boundary over 24 hours.
- The chlorine model: Fisher et al. (2012), Fisher (2022) and Fisher (2023), as in the PSM model.

**Equations** (t in hours):

```
dTW/dt = k*(Tsoil - TW)                                   tanks: adiabatic
k      = 3600*4*αw/(D^2*[1/Nu + λw*ln(D2/D)/(2λp) + λw*ln(D3/D2)/(2λs)])
Nu     = 0.027*Re^0.8*Pr^0.33 if Re > 5000, else 3.66
D2     = 1.052*D (PVC wall),  D3 = D2 + 2*TSoI*D          TSoI also switches at Re = 5000
θ      = exp(E/R*(TW - 20)/(293*(TW + 273)))              in kF, kS; θW, ν and DCL also at TW
```

| Coefficient | Value | From |
|---|---|---|
| αw | 0.14e-6 m²/s | Blokker et al. (2024) |
| λw, λp (PVC), λs (dry sand) | 0.57, 0.16, 1.6 W/m/K | Blokker et al. (2024) |
| D2/D, Pr, Re for the turbulent Nusselt number | 1.052, 7, 5000 | Table A8 |
| TSoI, laminar and turbulent | 2, 0.5 | 2 as recommended for laminar flow; 0.5 within the 0 to 1 recommended for turbulent flow |
| Tsoil | 20 °C | Chosen here: summer (Blokker et al. used 18 to 20.5 °C at the end of August) |
| Water at R1, R2 | 10 °C, 12 °C; 1.0 mg/L of chlorine | Chosen here |
| Chlorine kinetics, wall, by-products | As water A of the PSM model | Fisher (2022, 2023) |

**Deviations and assumptions**

- **Re is not corrected for temperature.** MSX's Re uses a fixed viscosity (about 20 °C), as Re effectively is in both source papers; at 10 °C it is about 25 % too high.
- **One soil temperature for all pipes.** Blokker's soil model, burial depth and other heat sources are not modelled; every pipe is taken as PVC, and tanks exchange no heat.
- **Sources and start.** Both reservoirs supply the same water, at different temperatures. The network starts with R1 water after 6 hours in a 100 mm laminar pipe (18.5 °C).

**On L-Town 24 h** the water warms from 10 to 12 °C at the reservoirs towards the soil's 20 °C; at 24 h the median over the network is 16.4 °C, and the 5th and 95th percentiles 11.5 and 19.2 °C. Cold water near the reservoirs loses chlorine more slowly (θ is 0.28 at 10 °C); chlorine ranges from 1.0 to 0.012 mg/L.

## Intrusion and inactivation

`ltown-inactivation.msx`: free chlorine decays in the bulk and at the wall, is consumed by the material of a two-hour intrusion at one junction, and inactivates four organisms whose chlorine resistance spans four orders of magnitude: *E. coli*, an enteric virus, *Mycobacterium aurum* and *Giardia* cysts. Chlorine exposure (CT), contact time and the log-inactivation credits for *Giardia* and *M. aurum* are carried as species. Inactivation follows Chick-Watson kinetics, with rate constants from CT values.

**Sources**

- USEPA (2020). *Disinfection Profiling and Benchmarking Technical Guidance Manual*. EPA 815-R-20-003. [epa.gov](https://www.epa.gov/sites/default/files/2020-06/documents/disprof_bench_3rules_final_508.pdf). Public. Tables B-1 and B-2 (CT for *Giardia* and viruses), and in Appendix H the CT regression of Smith, D.B., Clark, R.M., Pierce, B.K. and Regli, S. (1995), An empirical model for interpolating C·T values for chlorine inactivation of *Giardia lamblia*, *Journal of Water Supply: Research and Technology - AQUA* 44(5):203-211, used as printed there.
- Helbling, D.E. and VanBriesen, J.M. (2007). Free chlorine demand and cell survival of microbial suspensions. *Water Research* 41(19):4424-4434. [doi:10.1016/j.watres.2007.06.006](https://doi.org/10.1016/j.watres.2007.06.006). Subscription; the abstract, for the CT values of *E. coli* and *M. aurum* and the thresholds of cell-associated demand.
- Helbling, D.E. and VanBriesen, J.M. (2009). Modeling residual chlorine response to a microbial contamination event in drinking water distribution systems. *Journal of Environmental Engineering* 135(10):918-927. [doi:10.1061/(ASCE)EE.1943-7870.0000080](https://doi.org/10.1061/(ASCE)EE.1943-7870.0000080). Subscription; the abstract only. Its fast and slow demand (0.87 of it fast; 0.31 and 0.02 per hour) is taken from papers that cite it.
- Schijven, J., Forêt, J.M., Chardon, J., Teunis, P., Bouwknegt, M. and Tangena, B. (2016). Evaluation of exposure scenarios on intentional microbiological contamination in a drinking water distribution network. *Water Research* 96:148-154. [doi:10.1016/j.watres.2016.03.057](https://doi.org/10.1016/j.watres.2016.03.057). Subscription; the abstract, for an intrusion of 120 minutes and 10<sup>6</sup> or more organisms per litre.
- Macedo, D.O. and Janzen, J.G. (2022). Modelling the behaviour of chlorine within a drinking water distribution system following a microbial contamination event. *Urban Water Journal* 19(5). [doi:10.1080/1573062X.2022.2030370](https://doi.org/10.1080/1573062X.2022.2030370). Subscription; the abstract, which reports that the first-order description of Helbling and VanBriesen is not universal.
- The bulk and wall decay of the water: the manual's Listing 5.2.

**Equations** (t in minutes; organisms per litre):

```
dCL2/dt  = -(kb + kwall)*CL2 - kF2*CL2*DEMF - kS2*CL2*DEMS - (YEC*kEC*ECOLI + YMAU*kMAU*MYCO)*CL2
kwall    = (4/D)*kw*kf/(kw + kf), kf = Sh*Dmol/D, Sh = 0.0149*Re^0.88*Sc^(1/3) if Re > 2300, else 3.65
dDEMF/dt = -kF2*CL2*DEMF,   dDEMS/dt = -kS2*CL2*DEMS
dN/dt    = -kN*CL2*N                     N = ECOLI, VIRUS, MYCO (Chick-Watson, n = 1)
dGIARD/dt = -kG*CL2*GIARD,  kG = ln(1000)/CTG
CTG      = 1.059*(12.006 + exp(2.46 - 0.073*T + 0.125*CL2 + 0.389*pH))     CT for 3 logs of Giardia
dCT/dt = CL2,  dTAU/dt = 1,  dGLOG/dt = 3*CL2/CTG,  MLOG = 3*CT/42.9 (a formula)
```

Tanks have no wall term. The intrusion is six `MASS` sources at junction n136, all on one pattern that is 1 from 06:00 to 08:00.

| Coefficient | Value | From |
|---|---|---|
| kb | 0.3 per day | Listing 5.2 |
| kw | 0.5 m/day | Assumed, a usual value |
| Dmol, Sc | 1.2e-9 m²/s, 846.15 | Listing 5.2 |
| kF2, kS2 | 1.033e-2, 6.67e-4 L/(mg·min) | 0.31 and 0.02 per hour (Helbling and VanBriesen 2009) divided by 0.5 mg/L |
| kEC | 215.9 L/(mg·min) | ln(10<sup>3</sup>)/0.032: 3 logs of *E. coli* at a CT of 0.032 mg·min/L (Helbling and VanBriesen 2007) |
| kVIR | 1.535 L/(mg·min) | ln(10<sup>4</sup>)/6: 4 logs of viruses at a CT of 6 mg·min/L at 10 °C (USEPA 2020, Table B-2) |
| kMAU | 0.161 L/(mg·min) | ln(10<sup>3</sup>)/42.9: 3 logs of *M. aurum* (Helbling and VanBriesen 2007) |
| T, pH | 10 °C, 7.5 | Assumed; they enter only the *Giardia* regression |
| YEC, YMAU | 5e-11, 2e-9 mg of chlorine per cell | An order of magnitude, within the thresholds of Helbling and VanBriesen (2007) |
| Intrusion | 10 L/min: 10<sup>8</sup> *E. coli*, 10<sup>6</sup> viruses, 10<sup>4</sup> cysts and 10<sup>6</sup> *M. aurum* per litre; 30 mg/L of demand, 0.87 of it fast | Schijven et al. (2016); Helbling and VanBriesen (2009) |

At 10 °C and pH 7.5 the *Giardia* regression gives a CT for 3 logs of 130 and 138 mg·min/L at 0.5 and 1.0 mg/L of chlorine, against 125 and 134 in Table B-1, which it is meant to exceed slightly.

**Deviations and assumptions**

- **Demand that runs out.** Helbling and VanBriesen (2009) describe chlorine after a contamination as two parallel first-order decays, which never end. Here the fast and slow demand are pools that react second-order with chlorine, with the rate constants converted at 0.5 mg/L, where both forms give the same rate.
- **The cell-associated demand** (YEC, YMAU) is an order of magnitude, tied to the rate of inactivation, and small next to the demand pools.
- **No Hom model**: no exponent could be verified in an open source. Every organism follows Chick-Watson with n = 1; *Giardia*'s rate constant varies with chlorine through the regression.
- **A `MASS` source adds mass, not water**, so the intrusion does not dilute the chlorine.
- **The laminar Sherwood number is fixed at 3.65**, without the Graetz term, so that no expression divides by the pipe length.
- **Exposure keeps accumulating** after the organisms are gone: CT reaches about 660 mg·min/L in the tank.
- **Stiff.** At 0.5 mg/L the *E. coli* rate is about 108 per minute, against a 300 s step, hence ROS2 (RTOL 10<sup>−4</sup>, ATOL 10<sup>−6</sup>, tolerances per species). Tolerances 100 times tighter change chlorine at the reported nodes by less than 5·10<sup>−4</sup> (relative), and CT and the credits by less than 0.3 %.
- **Where the intrusion goes.** n136 was chosen with a tracer run: its water reaches 255 of the 782 junctions within 24 hours, and the intrusion is 6 to 22 % of the flow through it.

**On L-Town 24 h** chlorine stays between 0.043 and 1.0 mg/L. *E. coli* is undetectable 10 minutes downstream of the intrusion, where the virus has fallen from 1.6·10<sup>5</sup> to about 10<sup>2</sup> per litre and *M. aurum* still numbers about 3·10<sup>4</sup> per litre; 1.4 hours downstream only *Giardia* is left in appreciable numbers. The intrusion's demand lowers chlorine by 0.24 mg/L (38 %) just downstream and by 0.10 mg/L (23 %) 1.4 hours downstream.

## PODDS discolouration

`ltown-podds.msx` implements PODDS (Prediction Of Discolouration in Distribution Systems, University of Sheffield): material held on the pipe wall in layers of increasing shear strength. When the wall shear stress exceeds the strength of the weakest layer left, material erodes into the water as turbidity; when it does not, the layers slowly regenerate. Turbidity is in NTU, and the material on the wall in TPMU/m² (1 TPMU is 1 NTU·m³). PODDS has been run in EPANET-MSX by its authors (Husband, Xin and Boxall 2012, below), but that paper could not be obtained; this file is a new implementation of the published equations.

**Sources**

- Boxall, J.B. and Saul, A.J. (2005). Modeling discoloration in potable water distribution systems. *Journal of Environmental Engineering* 131(5):716-725. [doi:10.1061/(ASCE)0733-9372(2005)131:5(716)](https://doi.org/10.1061/(ASCE)0733-9372(2005)131:5(716)). Subscription; not consulted, its equations taken from the papers below.
- Husband, S. and Boxall, J. (2015). Predictive water quality modelling and resilience flow conditioning to manage discolouration risk in operational trunk mains. *Journal of Water Supply: Research and Technology - AQUA* 64(5):529-542. [doi:10.2166/aqua.2014.042](https://doi.org/10.2166/aqua.2014.042). The accepted manuscript is open in [White Rose Research Online](https://eprints.whiterose.ac.uk/id/eprint/90591/). The equations and their units.
- Husband, S. and Boxall, J. (2016). Understanding and managing discolouration risk in trunk mains. *Water Research* 107:127-140. [doi:10.1016/j.watres.2016.10.049](https://doi.org/10.1016/j.watres.2016.10.049). Open access (CC BY). The parameters, and regeneration as originally coded.
- Furnass, W.R. (2015). *Modelling both the continual accumulation and erosion of discolouration material in drinking water distribution systems.* PhD thesis, University of Sheffield. [White Rose eTheses](https://etheses.whiterose.ac.uk/id/eprint/10645/). Open access (CC BY-NC-ND). Equations 2.15 to 2.18, the parameter sets of Table 5.6 and the regeneration of Figures 4.6 and 5.9.
- Husband, P.S. and Boxall, J.B. (2010). Field studies of discoloration in water distribution systems: model verification and practical implications. *Journal of Environmental Engineering* 136(1):86-94. [doi:10.1061/(ASCE)EE.1943-7870.0000115](https://doi.org/10.1061/(ASCE)EE.1943-7870.0000115). Subscription; quoted through Furnass (2015).
- Husband, S., Boxall, J. and Sunny, I. (2023). Simulating long term discolouration behaviour in large diameter trunk mains. *Environmental Science: Water Research & Technology* 9(3):756-771. [doi:10.1039/d2ew00855f](https://doi.org/10.1039/d2ew00855f). Open access (CC BY). The regeneration period and the background turbidity.
- Husband, S., Xin, Y. and Boxall, J. (2012). Long term asset condition and discolouration modelling in water distribution systems with Epanet MSX. *World Environmental and Water Resources Congress 2012*, ASCE, 3161-3170. [doi:10.1061/9780784412312.317](https://doi.org/10.1061/9780784412312.317). Not obtained.

**Equations** (t in s; [x] is 1 when x is true, written with `STEP()`):

```
τa       = ρ*U^2*Ff/8                     applied wall shear stress (Pa)
τc       = (C - Cmax)/k                   strength of the weakest layer left (eq. 2.15)
R        = P*max(τa - τc, 0)^n*[C > 0]    erosion, TPMU/m²/s (eq. 2.16)
dC/dt    = P0*[τa < τc] - R               material on the wall (eq. 2.18, with regeneration)
dTURB/dt = 1000*Av*R                      R*4/D, which is R*As/Q through a pipe (eq. 2.17)
```

Tanks leave turbidity unchanged. τc and τa are also reported, as wall formulas.

| Coefficient | Value | From |
|---|---|---|
| k, P, n | -0.5 TPMU/m²/Pa; 2.0e-4 TPMU/m²/Pa<sup>n</sup>/s; 2.5 | Furnass (2015), Table 5.6, set PODDS-2 (a 100 mm pipe; 78 % of L-Town's pipes are 100 mm) |
| Cmax | 0.9 TPMU/m² | Chosen here: an ultimate strength, -Cmax/k, of 1.8 Pa, the upper value found in plastic pipes (Husband and Boxall 2010) |
| P0 | 1.6e-8 TPMU/m²/s | Chosen here: full regeneration in 1.75 years ("just over two years", Husband and Boxall 2015; 1.65 to 1.85 years, Husband et al. 2023) |
| Background turbidity | 0.1 NTU | Treated water at 0.05 to 0.2 NTU (Husband et al. 2023) |
| Initial state | C = Cmax + k·τcond | τcond is half the pipe's peak shear stress in the run, at least 0.02 Pa |

**Deviations and assumptions**

- **Regeneration.** The full law of Boxall and Saul (2005), with exponents for temperature and strength, could not be obtained. The file sets both to zero, giving a constant rate from the strongest layer to the weakest, which is how Furnass (2015) ran PODDS.
- **Illustrative coefficients.** The calibrated PODDS table by material and diameter is not published. The coefficients are `PARAMETER`s, so they can be set per pipe.
- **Conditioning per pipe.** PODDS assumes the layers are in equilibrium with a conditioning shear stress, usually the daily peak. Here it is half each pipe's own peak, so the day's peak flows are about 45 % above the conditioning flows, as on a hot day. One value for every pipe would start the busy mains above their strength and open the run with an artificial flush.
- **Shear stress from `U` and `Ff`**, because `Us` is read as `U` ([below](#msx-limitations-met-while-writing-them)).
- **State per segment.** MSX keeps wall species on the water segments, not on the pipe; with the same shear along a pipe and a uniform start, the segments evolve alike, as PODDS's per-pipe state does.
- **A 60 s step.** It is within 0.044 NTU of Euler with 10 s steps; a 300 s step is off by up to 0.13 NTU, mostly from transport in L-Town's many short pipes.

**On L-Town 24 h** node turbidity ranges from 0.10 to 0.38 NTU. It rises with the morning demand from 8 h and is highest at the evening peak, 18 to 22 h, when the median node reaches 0.20 NTU. 342 pipes lose material, while 554 end the day with slightly more than they started; the tank rises to 0.15 NTU.

## VCDM discolouration

`ltown-vcdm.msx` implements the Variable Condition Discolouration Model, the successor of PODDS. It describes the material on the wall by how much of it is held at each shear strength, φ(τ, t) between 0 and 1, so that weak material can erode while stronger material regenerates. The file holds one wall species per strength band, 17 in all; with turbidity and two reported wall formulas, that is 20 species in every pipe.

**Sources**

- Furnass, W.R., Collins, R.P., Husband, P.S., Sharpe, R.L., Mounce, S.R. and Boxall, J.B. (2014). Modelling both the continual erosion and regeneration of discolouration material in drinking water distribution systems. *Water Science and Technology: Water Supply* 14(1):81-90. [doi:10.2166/ws.2013.176](https://doi.org/10.2166/ws.2013.176). The accepted version is open in White Rose Research Online (eprint 87035); the journal version is subscription. Equations 1 to 3.
- Furnass (2015), as for PODDS: Table 6.5, the VCDM fitted to the PODDS-CI1 flushing data.
- Furnass, W.R., Mounce, S.R., Husband, S., Collins, R.P. and Boxall, J.B. (2019). Calibrating and validating a combined accumulation and mobilisation model for water distribution system discolouration using particle swarm optimisation. *Smart Water* 4:3. [doi:10.1186/s40713-019-0015-z](https://doi.org/10.1186/s40713-019-0015-z). Open access (CC BY). The same fit, and the "single cusp" initial state.
- Husband, Boxall and Sunny (2023), as for PODDS: the accumulation period.

**Equations** (t in s; [x] is 1 when x is true, written with `STEP()`):

```
dφi/dt   = -βe*(τa - si)*[τa > si]*[φi > 0] + βr*[τa < si]*[φi < 1]    i = 1..17 (eq. 1)
dN/dt    = α*Σi wi*βe*(τa - si)*[τa > si]*[φi > 0]                    release, TPMU/m²/s (eq. 3)
dTURB/dt = 1000*Av*dN/dt,   τa = ρ*U^2*Ff/8
si       = 0.01*sqrt(2)^(i-1) Pa (0.01 to 2.56 Pa),  wi = si*(2^(1/4) - 2^(-1/4))
```

The wall formulas report the material on the wall, α·Σ wi·φi, and τa.

| Coefficient | Value | From |
|---|---|---|
| βe | 6.4e-4 1/(Pa·s) | The VCDM fitted to the PODDS-CI1 flushing data (unlined cast iron, 95 mm): Furnass (2015), Table 6.5; Furnass et al. (2019) |
| α | 0.593 TPMU/(Pa·m²) | The same fit |
| βr | 1.81e-8 1/s | Chosen here: an accumulation period of 1.75 years (1.65 to 1.85 years, Husband et al. 2023) |
| Bands | 17, spaced geometrically | Chosen here |
| Initial state | φ = 0 below τcond, 1 above | The single cusp (Furnass 2015; Furnass et al. 2019), with τcond as for PODDS |

**Deviations and assumptions**

- **Geometric bands.** The papers use bands of equal width, 100 to 1000 of them (Husband et al. 2023 found 20 or more adequate on a trunk main). L-Town's shear stress spans three orders of magnitude, so the bands are spaced geometrically, and each band's width takes the place of dτ in equation 3.
- **No maximum strength**, as for cast iron in the fit used; the top band is at 2.56 Pa.
- **Euler**, as in the VCDM's reference code. MSX clips φ at 0 after a step, but the release uses the whole step's rate, so a band that empties within a step releases up to one step's erosion too much. Here a band takes 10 to 20 steps or more to empty.

**On L-Town 24 h** node turbidity ranges from 0.10 to 0.73 NTU, with the same daily pattern as PODDS (the network's maximum is at 20:10); the median node peaks at 0.38 NTU. 541 pipes lose material, and the tank rises to 0.21 NTU.

## On other networks

`tools/private-reactions.py --kinds literature` writes all seven models for another network, with the L-Town files as templates (`--kinds dbp,psm,podds` writes only those):

```
tools/private-reactions.py models/inp/nwmodel-12h.inp --kinds literature --name nw --out models/msx
```

The script:

- sets **`LU`**, the length-unit constant, to 1 for SI networks and 0.3048 for US units. MSX gives D, Len and U in the network's units; every file multiplies them by `LU` (the terms `DLU`, `LLU` and `ULU`), so that the coefficients stay in SI;
- maps L-Town's source waters, the `NODE R1` and `NODE R2` lines, onto the network's reservoirs: the R1 water to the first, third and so on, the R2 water to the second, fourth and so on (the R1 water again where the model has only one). The R1 water also goes as a `CONCEN` source to every junction with a negative demand;
- for PODDS and VCDM, conditions each pipe at half the peak wall shear stress it sees in the run (at least 0.02 Pa), from EPANET's hydraulics: ρ·g·(D/4)·head loss/length at every hydraulic step, with the EPANET library of the unpatched build;
- for the inactivation model, puts the intrusion at the junction with the most flow through it (at the middle of the intrusion), among the junctions at least three links from any reservoir, tank or junction where water enters. The intrusion starts at 06:00, or a quarter of the way into a shorter run, and lasts 2 hours, or a sixth of a shorter run, on the network's pattern time step;
- keeps the reported species, but not L-Town's report nodes.

`--cases literature-large` runs the files it wrote for two public networks, both in US units (`LU` 0.3048):

- `models/msx/nw-dbp.msx`, `nw-psm.msx` and so on, on NW Model 12 h: the R1 water at reservoirs 7384 and RES9000, the R2 water at 311, and the intrusion at junction 91 from 03:00 to 05:00;
- `models/msx/bwsn2-dbp.msx` and so on, on BWSN2 6 h: the R1 water at RESERVOIR-12523 and at JUNCTION-12500 (a negative demand), the R2 water at RESERVOIR-12524, and the intrusion at JUNCTION-5416 from 02:00 to 03:00, on BWSN2's hourly patterns.

**Dispersion on a larger network.** `--cases literature` also runs `bwsn2-dispersion.msx` on BWSN2 6 h (`bwsn2-disp`): the manual's Listing 5.2 with dispersion, as in the KY8 case, with the source at both reservoirs, on a network nine times the size of KY8.

## MSX limitations met while writing them

Three are listed with the other findings in [Found, not yet written up](../3-bug-fixes/README.md#found-not-yet-written-up). The files work around each:

- **`Us` is read as `U`.** Hydraulic variable names are matched by prefix, so the shear velocity is not available; PODDS and VCDM compute the wall shear stress as ρ·U²·Ff/8.
- **A minus sign after a closing bracket is read as part of a number**, so `(SC^0.66) - 1` does not parse; such powers get terms of their own (`SC66`).
- **`x^y` is 0 for x ≤ 0**, so a negative number squared is 0. The Swamee-Jain logarithm is squared by multiplication, and PODDS raises only the non-negative excess shear stress to the power n.

One more matters in practice. Where a pipe has no flow, MSX's `Ff` (the head loss divided by the flow squared) is infinite or NaN, and MSX sets a term that evaluates to NaN to 0 ([mathexpr.c:725](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/mathexpr.c#L725)), so the terms based on the shear stress drop out there: a stagnant pipe does not erode in PODDS and VCDM, and the DBP model's Gnielinski term gives 0, leaving the laminar branch.
