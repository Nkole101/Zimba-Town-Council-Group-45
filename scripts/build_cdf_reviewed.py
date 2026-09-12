"""Reproduce the manually reviewed CDF announcement snapshot from saved sources.

Review decisions are explicit below, not automated guesses. Dates and URLs come
from the saved WordPress archive. Run cdf_scraper.py first to collect evidence.
Repeated projects across different announcement dates are retained as updates.
"""
import csv
import json
from pathlib import Path

from cdf_scraper import OUTPUT_COLUMNS, OUTPUT_FILENAME

ROOT = Path(__file__).resolve().parents[1]
# post ID, project name, sector, stated place, amount, status, reviewed summary
REVIEWED = [
    (4201, "Siameja Community School 1x3 classroom block", "education", "Mapatizya", 1265906.80, "completed", "A 1x3 classroom block at Siameja Community School was commissioned at a stated cost of K1,265,906.80."),
    (4201, "Zimba Mission Hospital mothers' shelter ablution and water system", "water_sanitation", "Mapatizya", 600000, "completed", "An ablution block and water reticulation system at the mothers' shelter were commissioned under the 2025 CDF for K600,000."),
    (4180, "Mapatizya Clinic maternity annex", "health", "Mapatizya", "", "", "The article identifies a CDF maternity annex with an antenatal clinic and labour ward. Its conflicting attribution of the separate mothers' shelter is not used."),
    (4151, "Mulamfu Ward 20 agricultural water pumps monitoring", "agriculture", "Mulamfu", "", "", "The council monitored 20 CDF water pumps distributed the previous year to support winter farming. This is a monitoring update, not an additional procurement."),
    (4132, "Kabanga Secondary School and other schools desk provision", "education", "Simwatachela", "", "planned", "The 2026 approved CDF programme includes desks at Kabanga Secondary School and other schools enrolling Form One pupils."),
    (4132, "Misika Rural Health Centre staff house, water, waste and equipment", "health", "Misika", "", "planned", "Approved works comprise a staff house, water reticulation, waste management, beds, chairs and medical equipment. The source names Misika here without explicitly calling it a ward."),
    (4132, "Mafumba Rural Health Post staff house, waste system and equipment", "health", "Mafumba", "", "planned", "The government approved a staff house, waste management system, beds, chairs and medical equipment at Mafumba Rural Health Post."),
    (4132, "Chuundwe Ward rural health post", "health", "Chuundwe", "", "planned", "The approved programme includes commencement of a rural health post in Chuundwe Ward."),
    (4132, "Mooka Primary School 1x3 classroom block", "education", "Siamafumba", "", "planned", "A 1x3 classroom block will be constructed at Mooka Primary School under the approved 2026 programme."),
    (4132, "Syejumba Village rural health centre", "health", "Kanyanga", "", "planned", "The approved programme includes construction of a rural health centre at Syejumba Village in Kanyanga Ward."),
    (4132, "Sindowe Primary School 1x3 classroom block", "education", "Mangonda", "", "planned", "A 1x3 classroom block is approved for Sindowe Primary School in Mangonda Ward."),
    (4132, "Tore Shultz Primary School 1x3 classroom block", "education", "Zimba", "", "planned", "A 1x3 classroom block is approved for Tore Shultz Primary School in Zimba Ward."),
    (4132, "Simukanda Primary School 1x3 classroom block", "education", "Chidi", "", "planned", "A 1x3 classroom block is approved for Simukanda Primary School in Chidi Ward."),
    (4132, "Kakopa Primary School 1x3 classroom block", "education", "Luyaba", "", "planned", "A 1x3 classroom block is approved for Kakopa Primary School in Luyaba Ward."),
    (4100, "Presidential Initiatives solar plant", "infrastructure", "", "", "planned", "Contractors visited the proposed solar plant site opposite Dayow Beef under the 2026 CDF pre-bid process. No ward or project cost is stated."),
    (4055, "Mulamfu health facility maternity annex, staff houses and water system", "health", "Mulamfu", "", "near_completion", "The CDF-supported facility is nearing commissioning while plumbing and other remedial works are being completed."),
    (3792, "Nakowa Maternity Annex", "health", "Zimba", 1500000, "completed", "The Nakowa Maternity Annex was commissioned and handed over to the community at a stated construction cost of K1.5 million."),
    (3792, "Nakowa Maternity Annex accompanying water system", "water_sanitation", "Zimba", 270000, "completed", "The commissioned maternity facility's accompanying water system cost K270,000 and will also benefit surrounding residents."),
    (3792, "Zimba Mission Hospital mothers' shelter water improvement allocation", "water_sanitation", "Mapatizya", "", "planned", "The MP announced a CDF allocation to improve the water supply at the mothers' shelter without stating its amount."),
    (3792, "Treasure Compound water extension allocation", "water_sanitation", "Mapatizya", 800000, "planned", "The MP announced K800,000 allocated to extend water services to Treasure Compound. A separate same-day post reports the ground-breaking."),
    (3782, "Kamukkeza Village maternity annex", "health", "", 2099616.03, "completed", "The CDF-funded maternity annex was commissioned and handed over at a stated cost of K2,099,616.03. The village is named but its ward is not."),
    (3777, "Treasure Compound water supply ground-breaking", "water_sanitation", "Mapatizya", 800000, "planned", "A ground-breaking ceremony launched the K800,000 water supply project with pipes, a booster pump, tank stand and tank, scheduled to commence that month."),
    (3205, "Muzya Road rehabilitation", "infrastructure", "Mapatizya", "", "ongoing", "Road works were ongoing during inspection. The article says Muzya Road is part of a K3.2 million allocation, so that programme total is not assigned as this road's cost."),
    (3205, "Ackson Sejani Road rehabilitation", "infrastructure", "Mapatizya", "", "completed", "The council reports completion of rehabilitation of Ackson Sejani Road connecting to Kabanga Market."),
    (3193, "Siakasipa Community School 1x3 classroom block contract", "education", "Kanyanga", "", "planned", "A CDF contract was awarded to Size Entreprizes for a classroom block; contractors were expected to mobilize and commence works."),
    (3193, "Siameja Community School 1x3 classroom block contract", "education", "Mangonda", "", "planned", "A CDF contract was awarded to Lushann Powers Investment Ltd for a classroom block; contractors were expected to commence works."),
    (3193, "Simalundu Secondary School 1x3 science laboratory contract", "education", "Siamafumba", "", "planned", "A CDF contract was awarded to Tonacha General Dealers for a science laboratory at Simalundu Secondary School."),
    (3193, "Simundivwi Secondary School 1x3 classroom block contract", "education", "Chidi", "", "planned", "A CDF contract was awarded to Sternab Enterprise for a classroom block at Simundivwi Secondary School."),
    (3193, "Mafumba health post construction contract", "health", "Mafumba", "", "planned", "Zamtrek Contractors received the CDF contract for construction of a health post in Mafumba Ward."),
    (3193, "Misika Village rural health centre construction contract", "health", "Simwatachela", "", "planned", "Unlimited Eagle Contractors received the CDF contract for a rural health centre at Misika Village, stated here to be in Simwatachela Ward."),
    (2490, "Mulamfwu Ward 20 climate-resilient water pumps", "agriculture", "Mulamfwu", "", "completed", "Twenty climate-resilient water pumps were commissioned and handed over to five zones for year-round food production. The ward spelling is retained from the source."),
    (2477, "Muzya and Nkungwa 1x3 classroom blocks handover", "education", "Mapatizya", "", "completed", "Completed CDF classroom blocks in Muzya and Nkungwa were handed over, with solar systems and desks. The bundled announcement does not explicitly pair each community with a ward."),
    (2071, "Mapatizya climate-resilient boreholes programme", "water_sanitation", "Mapatizya", "", "ongoing", "Five of eleven earmarked boreholes had been drilled, with equipping and tank-stand installation continuing; a dry borehole was reported in Chuundwe. The article also reports a solar upgrade at Masanzya School."),
    (1689, "2024 CDF empowerment loans to 31 beneficiaries", "other", "Mapatizya", 1746232.59, "completed", "The council disbursed K1,746,232.59 in CDF empowerment loans to 31 beneficiaries. Completed refers to disbursement, not repayment or business outcomes."),
    (1518, "Mapatizya CDF ambulance procurement announcement", "health", "Mapatizya", "", "", "The minister stated that ambulances had been procured nationally using CDF and Mapatizya was expected to receive one that year. Delivery to the constituency was not confirmed."),
    (1479, "Zimba Secondary School industrial borehole", "water_sanitation", "Mapatizya", 240000, "", "K240,000 financed a 200-metre industrial borehole under the CDF disaster component. The article refers to the drilled facility but does not clearly establish completion of all works."),
    (982, "Muziya Primary School 1x3 classroom block", "education", "Mangonda", "", "completed", "The council listed the classroom block among completed 2022 CDF projects awaiting commissioning; the Muziya spelling is retained from this source."),
    (982, "Nkungwa Primary School 1x3 classroom block", "education", "Kanyanga", "", "completed", "The classroom block was listed among completed 2022 CDF projects awaiting commissioning."),
    (982, "Mulamfwu Ward clinic", "health", "Mulamfwu", "", "completed", "A clinic in Mulamfwu Ward was listed among completed 2022 CDF projects awaiting commissioning."),
    (982, "Mbwiko Ward clinic", "health", "Mbwiko", "", "completed", "A clinic in Mbwiko Ward was listed among completed 2022 CDF projects awaiting commissioning."),
    (982, "Cikuyu Primary School 1x3 classroom block", "education", "Chalimongela", "", "completed", "The classroom block was listed among completed 2022 CDF projects awaiting commissioning."),
    (911, "Mapatizya 2620 school desks distribution", "education", "Mapatizya", 2887051, "completed", "Distribution of 2,620 desks procured under 2022 and 2023 CDF was launched. The printed amount K 2, 887,051 is normalized by removing spaces and commas."),
    (911, "2023 CDF women and youth club grants", "other", "Mapatizya", 2143990, "completed", "K2,143,990 in grants was awarded to 65 women and youth clubs. Completed refers to the reported award, not subsequent activities."),
    (911, "2023 CDF cooperative and company loans", "other", "Mapatizya", "", "completed", "Loans were disbursed to 26 cooperatives and companies. The amount is left blank because the source prints the malformed figure K2, 93, 400."),
]


def main():
    archive = ROOT / "raw/cdf_projects/archive_snapshot.json"
    posts = {post["id"]: post for post in json.loads(archive.read_bytes())}
    rows = []
    for post_id, name, sector, place, amount, status, description in REVIEWED:
        post = posts[post_id]
        rows.append(dict(zip(OUTPUT_COLUMNS, ["", name, sector, place, "CDF", amount,
                                             status, post["date"][:10], description, post["link"]])))
    rows.sort(key=lambda row: (row["date_reported"], row["source_url"], row["project_name"]))
    for number, row in enumerate(rows, 1):
        row["project_id"] = f"ZTC-{number:03d}"
    target = ROOT / "data" / OUTPUT_FILENAME
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, delimiter="|")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} reviewed announcement records from {len(set(r['source_url'] for r in rows))} source posts to {target}")


if __name__ == "__main__":
    main()
