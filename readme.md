\# Gas Well Liquid Loading Screener v1



A Python tool for first‑pass screening of gas wells for liquid loading risk.  

Implements the \*\*Turner (1969)\*\*, \*\*Li (2001)\*\*, and \*\*Ikpeka \& Okolo (2018)\*\* critical velocity models, with correlations for gas density, liquid density, and surface tension.



\---



\## 📖 Background

This script is based on SPE literature and petroleum engineering correlations:

\- Turner, Hubbard \& Dukler (1969) – minimum flow rate for liquid removal

\- Coleman et al. (1991, SPE 20280) – wellhead conditions and fluid properties

\- Li et al. (2001) – modified critical velocity model

\- Ikpeka \& Okolo (2018) – blended velocity model

\- Sutton (1985, SPE 14265) – pseudo‑critical properties

\- Dranchuk \& Abou‑Kassem (1975) – Z‑factor EOS

\- McCain (1990) – water density correlation

\- Baker \& Swerdloff (1956) – oil/gas surface tension correlation



This tool is intended as a \*\*screening aid\*\*, not a full nodal analysis. Wells flagged here should be checked with a proper simulator (e.g. Prosper, GAP).



\---



\## ⚙️ Usage

Run the script directly:



```bash

python screener\_v1.py



