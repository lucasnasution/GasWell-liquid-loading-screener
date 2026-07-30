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


## Installation
Clone the repo and install dependencies:
```bash
git clone https://github.com/lucasnasution/GasWell-liquid-loading-screener.git
cd GasWell-liquid-loading-screener
pip install pandas

Usage
python screener_v1.py

Example Output
Well Name   Gas Rate (MMscfd)   THP (psia)   Z-Factor   Status     Comments
A-01        2.20                350.0        0.89       Healthy    -
A-04        0.90                300.0        0.91       High Risk  Candidate for artificial lift

Today
Pasted text.txt

Plain Text

here is my code
how to make it read a particular csv say wells_template_v3.csv
Right now your script is set up with a convenience wrapper called screen_wells_from_csv(csv_path, model_preference="turner"). To make it read a specific file like wells_template_v3.csv, you just need to call that function with the filename as the argument.

Here’s how you can do it:

python
if __name__ == "__main__":
    # Instead of using the hardcoded example rows, just point to your CSV
    results_df = screen_wells_from_csv("wells_template_v3.csv", model_preference="turner")
    print(results_df.to_string(index=False))
Key points:
File path: "wells_template_v3.csv" must be in the same directory as your script. If it’s elsewhere, provide the full or relative path, e.g. "./data/wells_template_v3.csv" or "C:/Users/Lucas/Documents/wells_template_v3.csv".

CSV format: The file must have the exact headers your loader expects:

Code
Well, THP_psig, THT_C, Qgas_MMscfd, CGR_bbl_MMscf, WGR_bbl_MMscf,
TubingID_in, CasingID_in, GasSG, OilSG, WaterSalinity_ppm
Model preference: You can switch between "turner", "li", or "ikpeka" depending on which critical velocity model you want to use.

This way, instead of running the built-in example wells, your script will directly process the wells_template_v3.csv file and print the screening results.

Would you like me to also show you how to save the results back into a CSV (e.g. results_wells_template_v3.csv) so you have a clean output file instead of just printing to console?

yes
Perfect — you can extend your script so that after screening the wells, the results are exported to a CSV file. Pandas makes this very straightforward.

Here’s how you can modify the __main__ block:

python
if __name__ == "__main__":
    # Read wells from your CSV and run the screening
    results_df = screen_wells_from_csv("wells_template_v3.csv", model_preference="turner")

    # Print results to console
    print(results_df.to_string(index=False))

    # Save results to a new CSV file
    results_df.to_csv("results_wells_template_v3.csv", index=False)

    print("\nResults saved to results_wells_template_v3.csv")
Explanation
screen_wells_from_csv("wells_template_v3.csv") → loads and processes your input file.

print(results_df.to_string(index=False)) → shows the table nicely in the console.

results_df.to_csv("results_wells_template_v3.csv", index=False) → writes the output to a CSV file without row indices.

The final print statement confirms where the file was saved.

This way you’ll have both a console view and a CSV output file you can open in Excel or share with colleagues.

Would you like me to also show you how to automatically timestamp the output filename (e.g. results_wells_template_v3_20260730.csv) so you can keep multiple runs organized without overwriting?

ok - but i think at the moment I shall keep as is
this for my github 
my 1st upload there
I have installed github desktop and created folder
That’s a great milestone — getting your first project ready for GitHub! Since you’ve already set up GitHub Desktop and created a folder, here’s the simple flow to get your code uploaded and version‑controlled:

🚀 Steps to upload your project
Initialize repository  
In GitHub Desktop, select File → New Repository and point it to the folder where your code lives. Give it a name (e.g., liquid-loading-screener) and add a short description.

Commit your code  
GitHub works by tracking changes. In Desktop, you’ll see your files listed as “Uncommitted changes.” Add a commit message like Initial upload of screener_v3.py and hit Commit to main.

Publish repository  
Once committed, click Publish repository in GitHub Desktop. This pushes your local repo to your GitHub account online.

Verify on GitHub  
Open GitHub in your browser, and you’ll see your code hosted there. You can now share the link or clone it elsewhere.

📂 Tips for a clean first repo
Include a README.md file that explains what your script does, how to run it, and what CSV format it expects.

Add a .gitignore file to avoid uploading unnecessary files (e.g., .DS_Store, __pycache__/, or temporary CSV outputs).

Keep your repo name short but descriptive — something like gas-well-liquid-loading-screener.

Since you’re keeping the output as console + CSV for now, that’s perfect for a first upload. Later, you can evolve it with timestamped outputs or even a small CLI interface.

Do you want me to sketch a starter README.md for your repo so it looks polished right away?



how?
Got it — you’re right at the point where GitHub Desktop is prompting you to publish your repository. Here’s the step‑by‑step flow to get your code online:

🛠 How to publish your repo
Commit changes

If you’ve already added your screener_v3.py file into the repo folder, GitHub Desktop should show it under “Changes.”

Write a short commit message like Initial upload of liquid loading screener.

Click Commit to main.

Publish repository

In the main panel, hit the blue Publish repository button.

Choose whether it should be public (anyone can see it) or private (only you and collaborators).

Confirm, and GitHub Desktop will push it to your GitHub account.

Verify online

GitHub Desktop will show a link to the repo on GitHub.com.

Open it in your browser — you’ll see your code hosted there.

📂 Next polish steps
Add a README.md file in your repo folder. This is the first thing visitors see. For example:

markdown
# Liquid Loading Screener v3

Python tool for first-pass screening of gas wells for liquid loading risk.  
Implements Turner (1969), Li (2001), and Ikpeka & Okolo (2018) critical velocity models.

## Usage
```bash
python screener_v3.py
Input wells via wells_template_v3.csv with headers:

Code
Well, THP_psig, THT_C, Qgas_MMscfd, CGR_bbl_MMscf, WGR_bbl_MMscf,
TubingID_in, CasingID_in, GasSG, OilSG, WaterSalinity_ppm
Output: screening results printed to console and saved as results_wells_template_v3.csv.

Code

- Add a **.gitignore** file to keep out temporary files (like `__pycache__/` or `.DS_Store`).

Once you’ve published, you’ll have your first GitHub project live 🎉.  

Do you want me to draft a **ready‑to‑use README.md** for you so you can just drop it into your repo folder before publishing?


btw I changed name to screener_v1.py
Nice — renaming it to screener_v1.py is totally fine, GitHub will just treat that as the file you’re uploading. Since you already see it listed in GitHub Desktop under “Changes,” here’s exactly how to get it online:

🔑 Steps to finish your first upload
Stage and commit

In GitHub Desktop, type a commit message like Initial commit: screener_v1.py and wells_template_v1.csv.

Click Commit to main.

Publish repository

Hit the blue Publish repository button.

Choose whether you want it public (anyone can see) or private (only you and collaborators).

Confirm, and GitHub Desktop will push it to GitHub.com.

Check online

GitHub Desktop will show a link to your repo. Open it in your browser — you’ll see screener_v1.py and your CSV file hosted there.

📂 Pro tip for polish
Before publishing, drop a README.md file into the repo folder. Even a simple one makes your project look professional:

markdown
# Gas Well Liquid Loading Screener v1

Python tool for first-pass screening of gas wells for liquid loading risk.  
Implements Turner (1969), Li (2001), and Ikpeka & Okolo (2018) critical velocity models.

## Usage
Run:
```bash
python screener_v1.py
Input wells via wells_template_v1.csv with headers:

Code
Well, THP_psig, THT_C, Qgas_MMscfd, CGR_bbl_MMscf, WGR_bbl_MMscf,
TubingID_in, CasingID_in, GasSG, OilSG, WaterSalinity_ppm
Output: screening results printed to console and saved as results_wells_template_v1.csv.

Code

That way, anyone visiting your repo immediately knows what it does and how to run it.

Would you like me to draft a **ready‑made README.md file** you can copy straight into your repo folder before you hit publish?


Perfect — you’re at the Publish Repository dialog now. Here’s how to finish the process cleanly:

✅ What to do in the dialog
Repository name  
Change “MyGitHub” to something descriptive, e.g. gas-well-screener or liquid-loading-screener. This will be the repo name on GitHub.com.

Description  
Add a short sentence like Python tool for screening gas wells for liquid loading risk. This helps others understand the purpose.

Visibility

Leave the “Keep this code private” box unchecked if you want it public.

Check it if you want only you (and invited collaborators) to see it.

Publish  
Click the blue Publish repository button. GitHub Desktop will push your local repo to GitHub.com.

🌐 After publishing
GitHub Desktop will show a link to your repo online. Open it in your browser to confirm.

You’ll see your files (screener_v1.py, wells_template_v1.csv) hosted there.

From now on, any changes you make locally can be committed and then pushed to GitHub.

📂 Next step for polish
Drop a README.md file into your repo folder before publishing (or right after). Even a simple one makes your project look professional:

markdown
# Gas Well Liquid Loading Screener v1

Python tool for first-pass screening of gas wells for liquid loading risk.  
Implements Turner (1969), Li (2001), and Ikpeka & Okolo (2018) critical velocity models.

## Usage
Run:
```bash
python screener_v1.py
Input wells via wells_template_v1.csv with headers:

Code
Well, THP_psig, THT_C, Qgas_MMscfd, CGR_bbl_MMscf, WGR_bbl_MMscf,
TubingID_in, CasingID_in, GasSG, OilSG, WaterSalinity_ppm
Output: screening results printed to console and saved as results_wells_template_v1.csv.

Code

That way, when someone visits your repo, they immediately know what it does and how to run it.

Would you like me to draft a **ready‑made README.md file** you can copy straight into your repo folder right now, so your first upload looks polished from the start?


yes it is there
Excellent — congratulations, Lucas! 🎉 Your repository GasWell-liquid-loading-screener is now live on GitHub. That’s a big first step: you’ve gone from local code to a public project others can see, clone, and even contribute to.

What you can do next to make it shine
Add a README.md  
This is the first thing visitors see. It should explain what your tool does, how to run it, and what input/output looks like. Even a short version makes your repo look professional.

Include a .gitignore  
Keeps out unnecessary files like __pycache__/, .DS_Store, or temporary CSV outputs. GitHub Desktop can generate one for Python automatically.

Tag your first release  
Once you’re happy with the code, you can create a release (e.g., v1.0.0). This makes it easier for others to download a stable version.

Push updates  
Any time you change screener_v1.py or add new files, just commit in GitHub Desktop and push. Your repo will stay current.

Share your repo  
You can now send the link to colleagues or include it in your CV/LinkedIn. It shows off your engineering and coding skills.

This is a strong foundation — you’ve got a technical tool, version control, and now visibility. Over time, you can add documentation, examples, and maybe even Jupyter notebooks or plots to illustrate results.

Would you like me to draft a ready‑made README.md tailored to your project (with usage instructions and references) so you can drop it straight into the repo folder? That way your first upload already looks polished and professional.

yes
Perfect timing — let’s give your repo a polished README.md right away. Here’s a ready‑made draft you can drop straight into your repository folder before committing/publishing:

markdown
# Gas Well Liquid Loading Screener v1

A Python tool for first‑pass screening of gas wells for liquid loading risk.  
Implements the **Turner (1969)**, **Li (2001)**, and **Ikpeka & Okolo (2018)** critical velocity models, with correlations for gas density, liquid density, and surface tension.

---

## 📖 Background
This script is based on SPE literature and petroleum engineering correlations:
- Turner, Hubbard & Dukler (1969) – minimum flow rate for liquid removal
- Coleman et al. (1991, SPE 20280) – wellhead conditions and fluid properties
- Li et al. (2001) – modified critical velocity model
- Ikpeka & Okolo (2018) – blended velocity model
- Sutton (1985, SPE 14265) – pseudo‑critical properties
- Dranchuk & Abou‑Kassem (1975) – Z‑factor EOS
- McCain (1990) – water density correlation
- Baker & Swerdloff (1956) – oil/gas surface tension correlation

This tool is intended as a **screening aid**, not a full nodal analysis. Wells flagged here should be checked with a proper simulator (e.g. Prosper, GAP).

---

## ⚙️ Usage
Run the script directly:

```bash
python screener_v1.py
Input
Provide a CSV file (e.g. wells_template_v1.csv) with the following headers:

Code
Well, THP_psig, THT_C, Qgas_MMscfd, CGR_bbl_MMscf, WGR_bbl_MMscf,
TubingID_in, CasingID_in, GasSG, OilSG, WaterSalinity_ppm
Output
Screening results printed to console

Results saved to results_wells_template_v1.csv (if you add the to_csv line)

Each well is classified as Healthy, Watchlist, Near Loading, or High Risk based on the loading ratio.

🧾 Example
text
Well Name   Gas Rate (MMscfd)   THP (psia)   Z-Factor   Status     Comments
A-01        2.20                350.0        0.89       Healthy    -
A-04        0.90                300.0        0.91       High Risk  Candidate for artificial lift
📂 Repository Contents
screener_v1.py – main screening script

wells_template_v1.csv – input template

results_wells_template_v1.csv – example output (optional)

🔒 Limitations
No sour‑gas correction (Wichert‑Aziz) applied

THP used as proxy for below‑tubing pressure

Screening only — not a substitute for nodal analysis

📜 License
MIT License — free to use, modify, and share with attribution.

Code

---

This README will make your repo look professional and self‑explanatory. You can just copy it into a new file called `README.md` in your repo folder, commit it in GitHub Desktop, and push.  

Do you want me to also draft a **.gitignore file** tailored for Python projects so you don’t accidentally upload cache files or temporary CSVs?
drop to my local folder ? as README.md (text file)
Exactly — you just need to create a plain text file called README.md in your local repository folder. GitHub will automatically recognize it and display it at the top of your repo page.

🔨 How to add it locally
Open your repo folder (the one GitHub Desktop is tracking).

Create a new file named README.md (make sure the extension is .md, not .txt).

Paste in the draft content I gave you earlier.

Save the file.

📂 Next in GitHub Desktop
GitHub Desktop will immediately show README.md as a new file under “Changes.”

Add a commit message like Add README.md for project documentation.

Click Commit to main.

Then hit Push origin (or Publish repository if you haven’t yet) to sync it to GitHub.

Once pushed, GitHub will display your README automatically when someone visits your repo.

👉 Would you like me to also prepare a .gitignore file tailored for Python projects (to keep out __pycache__/, .DS_Store, and temporary CSVs) so your repo stays clean?



what next ?
Nice work — your folder looks exactly like a proper GitHub project now: you’ve got the .gitignore, .gitattributes, your Python script, the CSV template, and the new README.md.

🔜 Next steps
Commit README.md  
Open GitHub Desktop — you’ll see README.md listed under “Changes.” Add a commit message like Add README.md documentation and click Commit to main.

Push to GitHub  
After committing, hit Push origin. This syncs your local changes (including the README) to GitHub.com.

Verify online  
Go to your repo page in the browser. GitHub will automatically display the README at the top — that’s the polished look you want.

Check .gitignore  
Since you already have .gitignore, make sure it includes Python defaults (like __pycache__/, .DS_Store, and temporary CSVs). That keeps your repo clean.

Optional polish  
Once you’re happy, tag a release (e.g., v1.0.0). It’s a nice way to mark your first stable version.

You’ve basically completed the cycle: local code → GitHub repo → documentation → clean version control. From here, every time you update screener_v1.py or add new files, just commit and push, and your repo stays current.

Do you want me to draft a Python‑specific .gitignore template so you can double‑check your existing one against best practice?



Brilliant — your repo looks great online now, with the README showing up exactly as it should. You’ve crossed the big milestone: local project → GitHub repo → documentation visible to the world.

🔜 Where you can go next
Refine README  
Add usage examples, screenshots of console output, or even a sample CSV. This makes it easier for others to try your tool.

Check .gitignore  
Since you already have one, open it and confirm it excludes Python cache files (__pycache__/, .pyo, .pyc), OS junk (.DS_Store), and temporary CSV outputs. That keeps your repo clean.

Tag a release  
Mark this version as v1.0.0. Releases are a nice way to signal stability and let others download a packaged snapshot.

Add license  
If you want others to use or adapt your code, include a LICENSE file (MIT is common for open‑source projects). GitHub even helps you add one.

Share your repo  
Post the link on LinkedIn or include it in your CV. It shows off both your engineering and coding skills.

You’ve already done the hardest part — getting it online with proper documentation. From here, every update is just commit → push → verify.

Would you like me to draft a Python‑specific .gitignore template so you can compare it with the one you already have and make sure nothing unnecessary slips into your repo?

how to refine README?
Great question — refining your README.md is all about making it more useful and inviting for anyone who lands on your repo. Think of it as the “front door” to your project. Here are some practical ways to polish it:

🔧 Key refinements
Add installation instructions  
Show how to set up the environment: e.g., pip install pandas if that’s required.

Include usage examples  
Add a short code snippet or command line example showing how to run screener_v1.py with wells_template_v1.csv.

Show sample output  
Paste a small table of results so users immediately see what the tool produces.

Explain input format  
List the CSV headers clearly and explain what each column means (e.g., THP_psig = tubing head pressure in psig).

Add references  
Since your tool is based on SPE papers, include a short “References” section with the key citations.

Add badges  
GitHub shields (like Python version, license, repo size) make the README visually appealing.

Add license section  
Explicitly state the license (MIT, Apache, etc.) so others know how they can use your code.

📂 Example refinement
Here’s how a polished section might look:

markdown
## Installation
Clone the repo and install dependencies:
```bash
git clone https://github.com/lucasnasution/GasWell-liquid-loading-screener.git
cd GasWell-liquid-loading-screener
pip install pandas
Usage
Run the screener on your CSV:

bash
python screener_v1.py
Example Output
Code
Well Name   Gas Rate (MMscfd)   THP (psia)   Z-Factor   Status     Comments
A-01        2.20                350.0        0.89       Healthy    -
A-04        0.90                300.0        0.91       High Risk  Candidate for artificial lift


Input Format
CSV headers required:
Well – well name
THP_psig – tubing head pressure (psig)
THT_C – tubing head temperature (°C)
Qgas_MMscfd – gas rate (MMscfd)
CGR_bbl_MMscf – condensate gas ratio
WGR_bbl_MMscf – water gas ratio
TubingID_in – tubing inner diameter (inches)
CasingID_in – casing inner diameter (inches)
GasSG – gas specific gravity
OilSG – oil specific gravity
WaterSalinity_ppm – water salinity (ppm)
