# data.py
# Shared reference data for UK letting agency document generation pipeline.
# All 250 documents across 8 batches import from this file.
# Usage: from data import *

import datetime

# ---------------------------------------------------------------------------
# 1. LETTING AGENCIES (7)
# ---------------------------------------------------------------------------

AGENCIES = {
    "belvoir": {
        "key": "belvoir",
        "name": "Belvoir Lettings Harlow",
        "address": "2 Post Office Road, Harlow, Essex, CM20 1DH",
        "phone": "01279 451 900",
        "email": "harlow@belvoir.co.uk",
        "vat_number": "GB 312 4421 07",
        "company_number": "08841203",
    },
    "future_let": {
        "key": "future_let",
        "name": "Future Let",
        "address": "14 The Rows, Harvey Centre, Harlow, Essex, CM20 1XJ",
        "phone": "01279 431 333",
        "email": "info@futurelet.co.uk",
        "vat_number": "GB 198 7743 12",
        "company_number": "06124578",
    },
    "leaders": {
        "key": "leaders",
        "name": "Leaders",
        "address": "18 Broad Walk, Harlow, Essex, CM20 1HX",
        "phone": "01279 420 220",
        "email": "harlow@leaders.co.uk",
        "vat_number": "GB 441 2291 03",
        "company_number": "02842219",
    },
    "haart": {
        "key": "haart",
        "name": "haart Harlow",
        "address": "20 East Gate, Harlow, Essex, CM20 1HP",
        "phone": "01279 452 600",
        "email": "harlow@haart.co.uk",
        "vat_number": "GB 229 8812 44",
        "company_number": "01900766",
    },
    "geoffrey_matthew": {
        "key": "geoffrey_matthew",
        "name": "Geoffrey Matthew Estate Agents",
        "address": "6 South Street, Bishop's Stortford, Hertfordshire, CM23 3AZ",
        "phone": "01279 657 800",
        "email": "lettings@geoffreymatthew.co.uk",
        "vat_number": "GB 371 5530 19",
        "company_number": "03987221",
    },
    "kings_group": {
        "key": "kings_group",
        "name": "Kings Group",
        "address": "3 Terminus Street, Harlow, Essex, CM20 1DZ",
        "phone": "01279 430 830",
        "email": "harlow@kingsgroup.co.uk",
        "vat_number": "GB 155 6627 81",
        "company_number": "07231489",
    },
    "intercounty": {
        "key": "intercounty",
        "name": "Intercounty",
        "address": "26 Market Square, Bishop's Stortford, Hertfordshire, CM23 3UY",
        "phone": "01279 712 100",
        "email": "bishops@intercounty.co.uk",
        "vat_number": "GB 274 1193 06",
        "company_number": "01337844",
    },
}


# ---------------------------------------------------------------------------
# 2. LANDLORDS (8)
# ---------------------------------------------------------------------------

LANDLORDS = {
    "thornton": {
        "key": "thornton",
        "name": "Mr. David Thornton",
        "first_name": "David",
        "last_name": "Thornton",
        "email": "david.thornton72@gmail.com",
        "phone": "07712 334 981",
        "address": "48 Riddings Lane, Harlow, Essex, CM19 4DE",
        "ni_number": "NJ 48 20 31 C",
    },
    "kapoor": {
        "key": "kapoor",
        "name": "Mrs. Priya Kapoor",
        "first_name": "Priya",
        "last_name": "Kapoor",
        "email": "priya.kapoor@hotmail.co.uk",
        "phone": "07843 201 556",
        "address": "12 Longbanks, Harlow, Essex, CM18 7AP",
        "ni_number": "ST 72 41 88 A",
    },
    "okonkwo": {
        "key": "okonkwo",
        "name": "Mr. Emeka Okonkwo",
        "first_name": "Emeka",
        "last_name": "Okonkwo",
        "email": "e.okonkwo@okonkwoproperties.co.uk",
        "phone": "07958 774 220",
        "address": "3 Parndon Mill Lane, Harlow, Essex, CM20 2HP",
        "ni_number": "PK 90 55 17 B",
    },
    "webb": {
        "key": "webb",
        "name": "Ms. Sandra Webb",
        "first_name": "Sandra",
        "last_name": "Webb",
        "email": "sandrawebb_lets@btinternet.com",
        "phone": "07601 118 439",
        "address": "91 London Road, Bishops Stortford, Hertfordshire, CM23 5ND",
        "ni_number": "YA 34 76 02 D",
    },
    "petrov": {
        "key": "petrov",
        "name": "Mr. Nikolai Petrov",
        "first_name": "Nikolai",
        "last_name": "Petrov",
        "email": "n.petrov.property@gmail.com",
        "phone": "07733 882 011",
        "address": "7 Tawneys Road, Harlow, Essex, CM18 6SN",
        "ni_number": "ZX 11 83 44 C",
    },
    "mensah": {
        "key": "mensah",
        "name": "Dr. Abena Mensah",
        "first_name": "Abena",
        "last_name": "Mensah",
        "email": "abena.mensah@nhs.net",
        "phone": "07920 645 321",
        "address": "19 Commonside Road, Harlow, Essex, CM18 6YH",
        "ni_number": "MN 62 29 77 A",
    },
    "obrien": {
        "key": "obrien",
        "name": "Mr. Patrick O'Brien",
        "first_name": "Patrick",
        "last_name": "O'Brien",
        "email": "pat.obrien1964@yahoo.co.uk",
        "phone": "07811 557 943",
        "address": "45 Potter Street, Harlow, Essex, CM17 9BT",
        "ni_number": "LW 48 90 23 B",
    },
    "chen": {
        "key": "chen",
        "name": "Mrs. Li Chen",
        "first_name": "Li",
        "last_name": "Chen",
        "email": "li.chen.properties@gmail.com",
        "phone": "07955 003 771",
        "address": "82 Fennells, Harlow, Essex, CM18 7LT",
        "ni_number": "AK 77 14 55 D",
    },
}


# ---------------------------------------------------------------------------
# 3. TENANTS (18 people, forming ~13 tenancies — singles and couples)
# ---------------------------------------------------------------------------

TENANTS = {
    "sharma_r": {
        "key": "sharma_r",
        "name": "Mr. Rohan Sharma",
        "first_name": "Rohan",
        "last_name": "Sharma",
        "email": "rohan.sharma91@gmail.com",
        "phone": "07444 213 678",
        "address": "Previous: 22 Brays Grove, Harlow, Essex, CM18 7LW",
    },
    "williams_k": {
        "key": "williams_k",
        "name": "Ms. Karen Williams",
        "first_name": "Karen",
        "last_name": "Williams",
        "email": "k.williams84@outlook.com",
        "phone": "07512 998 302",
        "address": "Previous: 4 Abercrombie Way, Harlow, Essex, CM20 2JU",
    },
    "kowalski_t": {
        "key": "kowalski_t",
        "name": "Mr. Tomasz Kowalski",
        "first_name": "Tomasz",
        "last_name": "Kowalski",
        "email": "t.kowalski@gmail.com",
        "phone": "07688 441 229",
        "address": "Previous: 17 Haydens Road, Harlow, Essex, CM19 5BB",
    },
    "kowalski_a": {
        "key": "kowalski_a",
        "name": "Ms. Agnieszka Kowalski",
        "first_name": "Agnieszka",
        "last_name": "Kowalski",
        "email": "agnieszka.kowalski@gmail.com",
        "phone": "07709 882 114",
        "address": "Previous: 17 Haydens Road, Harlow, Essex, CM19 5BB",
    },
    "adeyemi_j": {
        "key": "adeyemi_j",
        "name": "Mr. James Adeyemi",
        "first_name": "James",
        "last_name": "Adeyemi",
        "email": "james.adeyemi@hotmail.com",
        "phone": "07834 771 553",
        "address": "Previous: 9 Orchard Croft, Harlow, Essex, CM20 3AX",
    },
    "patel_n": {
        "key": "patel_n",
        "name": "Ms. Neha Patel",
        "first_name": "Neha",
        "last_name": "Patel",
        "email": "neha.patel@yahoo.co.uk",
        "phone": "07766 334 891",
        "address": "Previous: 33 The Rows, Harlow, Essex, CM20 1XP",
    },
    "patel_v": {
        "key": "patel_v",
        "name": "Mr. Vishal Patel",
        "first_name": "Vishal",
        "last_name": "Patel",
        "email": "vishal.patel87@gmail.com",
        "phone": "07801 224 667",
        "address": "Previous: 33 The Rows, Harlow, Essex, CM20 1XP",
    },
    "singh_h": {
        "key": "singh_h",
        "name": "Mr. Harpreet Singh",
        "first_name": "Harpreet",
        "last_name": "Singh",
        "email": "h.singh.harlow@gmail.com",
        "phone": "07944 667 112",
        "address": "Previous: 66 Barn Mead, Harlow, Essex, CM20 2XE",
    },
    "murphy_c": {
        "key": "murphy_c",
        "name": "Ms. Claire Murphy",
        "first_name": "Claire",
        "last_name": "Murphy",
        "email": "clairemurphy@live.co.uk",
        "phone": "07521 880 337",
        "address": "Previous: 5 Trotters Road, Harlow, Essex, CM20 1LB",
    },
    "nguyen_p": {
        "key": "nguyen_p",
        "name": "Mr. Phong Nguyen",
        "first_name": "Phong",
        "last_name": "Nguyen",
        "email": "phong.nguyen@gmail.com",
        "phone": "07677 109 423",
        "address": "Previous: 11 Maddox Road, Harlow, Essex, CM20 2JY",
    },
    "ali_s": {
        "key": "ali_s",
        "name": "Ms. Sara Ali",
        "first_name": "Sara",
        "last_name": "Ali",
        "email": "sara.ali93@gmail.com",
        "phone": "07392 558 801",
        "address": "Previous: 8 Glebelands, Harlow, Essex, CM20 3AJ",
    },
    "jones_m": {
        "key": "jones_m",
        "name": "Mr. Matthew Jones",
        "first_name": "Matthew",
        "last_name": "Jones",
        "email": "mattjones1989@hotmail.co.uk",
        "phone": "07800 342 190",
        "address": "Previous: 14 Fifth Avenue, Harlow, Essex, CM20 2LQ",
    },
    "jones_e": {
        "key": "jones_e",
        "name": "Ms. Emily Jones",
        "first_name": "Emily",
        "last_name": "Jones",
        "email": "emilyjones.harlow@gmail.com",
        "phone": "07892 441 003",
        "address": "Previous: 14 Fifth Avenue, Harlow, Essex, CM20 2LQ",
    },
    "nowak_f": {
        "key": "nowak_f",
        "name": "Mr. Filip Nowak",
        "first_name": "Filip",
        "last_name": "Nowak",
        "email": "filip.nowak@gmail.com",
        "phone": "07551 223 894",
        "address": "Previous: 3 Kitson Way, Harlow, Essex, CM20 1DQ",
    },
    "singh_a": {
        "key": "singh_a",
        "name": "Ms. Amrit Singh",
        "first_name": "Amrit",
        "last_name": "Singh",
        "email": "amrit.singh@outlook.com",
        "phone": "07430 776 552",
        "address": "Previous: 21 Abbotsweld, Harlow, Essex, CM18 6RP",
    },
    "thompson_g": {
        "key": "thompson_g",
        "name": "Mr. George Thompson",
        "first_name": "George",
        "last_name": "Thompson",
        "email": "george.thompson@yahoo.co.uk",
        "phone": "07622 338 114",
        "address": "Previous: 55 Gilden Way, Harlow, Essex, CM17 0LW",
    },
    "osei_k": {
        "key": "osei_k",
        "name": "Ms. Kwame Osei",
        "first_name": "Kwame",
        "last_name": "Osei",
        "email": "kwame.osei@gmail.com",
        "phone": "07771 990 224",
        "address": "Previous: 30 South Road, Harlow, Essex, CM20 2BD",
    },
    "hassan_z": {
        "key": "hassan_z",
        "name": "Mr. Zaid Hassan",
        "first_name": "Zaid",
        "last_name": "Hassan",
        "email": "zaid.hassan.uk@gmail.com",
        "phone": "07480 663 011",
        "address": "Previous: 44 Broadfield, Harlow, Essex, CM20 3PB",
    },
}


# ---------------------------------------------------------------------------
# 4. PROPERTIES (15)
# ---------------------------------------------------------------------------

PROPERTIES = {
    "mandarin_drive": {
        "key": "mandarin_drive",
        "address": "14 Mandarin Drive",
        "city": "Harlow",
        "postcode": "CM17 9QT",
        "property_type": "2-bed terraced house",
        "furnished": "Unfurnished",
        "monthly_rent": 1150.00,
        "landlord_key": "thornton",
        "agent_key": "belvoir",
        "num_bedrooms": 2,
        "epc_rating": "D",
        "epc_score": 62,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 1994,
        "consumer_unit": "Hager VML916CPD 16-way",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Vaillant ecoTEC Plus 831", "location": "Kitchen", "flue_type": "Balanced flue"},
            {"type": "Gas Hob", "make_model": "Zanussi ZGG65414BA", "location": "Kitchen", "flue_type": "N/A"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "barn_mead": {
        "key": "barn_mead",
        "address": "47 Barn Mead",
        "city": "Harlow",
        "postcode": "CM20 2XE",
        "property_type": "1-bed flat",
        "furnished": "Furnished",
        "monthly_rent": 825.00,
        "landlord_key": "kapoor",
        "agent_key": "future_let",
        "num_bedrooms": 1,
        "epc_rating": "C",
        "epc_score": 77,
        "eicr_result": "Satisfactory",
        "eicr_observations": [
            {"item": "1", "description": "No RCD protection to socket circuits", "code": "C3", "location": "Consumer Unit"},
        ],
        "installation_age": 2007,
        "consumer_unit": "Wylex NHRS8LSBS 8-way",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Worcester Bosch Greenstar 25i", "location": "Hallway cupboard", "flue_type": "Balanced flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "gilden_way": {
        "key": "gilden_way",
        "address": "83 Gilden Way",
        "city": "Harlow",
        "postcode": "CM17 0LW",
        "property_type": "3-bed semi-detached",
        "furnished": "Unfurnished",
        "monthly_rent": 1350.00,
        "landlord_key": "okonkwo",
        "agent_key": "haart",
        "num_bedrooms": 3,
        "epc_rating": "D",
        "epc_score": 59,
        "eicr_result": "Unsatisfactory",
        "eicr_observations": [
            {"item": "1", "description": "Dead end spur creating overloaded socket circuit", "code": "C2", "location": "Living Room Ring Circuit"},
            {"item": "2", "description": "Consumer unit lacks surge protection device", "code": "C3", "location": "Consumer Unit"},
        ],
        "installation_age": 1988,
        "consumer_unit": "MEM Memshield 2 (old metal clad)",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Baxi Platinum 24HE", "location": "Kitchen", "flue_type": "Balanced flue"},
            {"type": "Gas Hob", "make_model": "Hotpoint GC640TX", "location": "Kitchen", "flue_type": "N/A"},
            {"type": "Gas Fire", "make_model": "Valor Inspire 400 Slide", "location": "Living Room", "flue_type": "Open flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": "Fireplace flue requires monitoring — minor sooting observed on surround",
    },
    "parndon_mill": {
        "key": "parndon_mill",
        "address": "2A Parndon Mill Lane",
        "city": "Harlow",
        "postcode": "CM20 2HP",
        "property_type": "Studio flat",
        "furnished": "Furnished",
        "monthly_rent": 650.00,
        "landlord_key": "thornton",
        "agent_key": "belvoir",
        "num_bedrooms": 0,
        "epc_rating": "E",
        "epc_score": 48,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 1975,
        "consumer_unit": "Crabtree Starbreaker 6-way (old)",
        "gas_appliances": [
            {"type": "Back Boiler", "make_model": "Potterton Powermax 155X", "location": "Living area", "flue_type": "Open flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": "Back boiler approaching end of serviceable life. Recommend replacement within 2 years.",
    },
    "fennells": {
        "key": "fennells",
        "address": "19 Fennells",
        "city": "Harlow",
        "postcode": "CM18 7LT",
        "property_type": "2-bed flat",
        "furnished": "Partly furnished",
        "monthly_rent": 975.00,
        "landlord_key": "kapoor",
        "agent_key": "leaders",
        "num_bedrooms": 2,
        "epc_rating": "C",
        "epc_score": 74,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 2010,
        "consumer_unit": "Schneider Electric REARO12S 12-way",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Ideal Logic+ Combi 30", "location": "Airing cupboard", "flue_type": "Balanced flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "abbotsweld": {
        "key": "abbotsweld",
        "address": "7 Abbotsweld",
        "city": "Harlow",
        "postcode": "CM18 6RP",
        "property_type": "3-bed semi-detached",
        "furnished": "Unfurnished",
        "monthly_rent": 1275.00,
        "landlord_key": "webb",
        "agent_key": None,
        "num_bedrooms": 3,
        "epc_rating": "F",
        "epc_score": 34,
        "eicr_result": "Unsatisfactory",
        "eicr_observations": [
            {"item": "1", "description": "Absence of earthing conductor at consumer unit", "code": "C1", "location": "Consumer Unit / Meter Tails"},
            {"item": "2", "description": "Accessible live parts at back of old consumer unit", "code": "C1", "location": "Consumer Unit"},
            {"item": "3", "description": "No RCD protection to bathroom circuit", "code": "C2", "location": "Bathroom"},
        ],
        "installation_age": 1967,
        "consumer_unit": "Wylex Standard (fuse board — original)",
        "gas_appliances": [
            {"type": "Regular Boiler", "make_model": "Ideal Classic FF380", "location": "Airing cupboard", "flue_type": "Open flue"},
            {"type": "Gas Hob", "make_model": "Creda CRG310", "location": "Kitchen", "flue_type": "N/A"},
            {"type": "Gas Fire", "make_model": "Valor Blenheim 2 (outmoded)", "location": "Dining Room", "flue_type": "Open flue"},
        ],
        "gas_result": "FAIL",
        "gas_defects": "Gas fire flue blocked — products of combustion not venting correctly. Immediately Dangerous (ID) classification. Fire isolated and landlord notified.",
        "gas_warnings": "Boiler overheat thermostat faulty — At Risk (AR) classification. Do not use until repaired.",
    },
    "maddox_road": {
        "key": "maddox_road",
        "address": "38 Maddox Road",
        "city": "Harlow",
        "postcode": "CM20 2JY",
        "property_type": "2-bed terraced house",
        "furnished": "Unfurnished",
        "monthly_rent": 1095.00,
        "landlord_key": "petrov",
        "agent_key": "kings_group",
        "num_bedrooms": 2,
        "epc_rating": "D",
        "epc_score": 56,
        "eicr_result": "Satisfactory",
        "eicr_observations": [
            {"item": "1", "description": "Socket outlet with cracked faceplate — potential shock risk if energised", "code": "C3", "location": "Bedroom 2"},
        ],
        "installation_age": 1999,
        "consumer_unit": "Hager VML916CPD 16-way",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Vaillant ecoTEC Plus 618", "location": "Kitchen", "flue_type": "Balanced flue"},
            {"type": "Gas Hob", "make_model": "NEFF T26DS49N0", "location": "Kitchen", "flue_type": "N/A"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "potter_street": {
        "key": "potter_street",
        "address": "12 Potter Street",
        "city": "Harlow",
        "postcode": "CM17 9BT",
        "property_type": "4-bed detached",
        "furnished": "Unfurnished",
        "monthly_rent": 1800.00,
        "landlord_key": "okonkwo",
        "agent_key": "belvoir",
        "num_bedrooms": 4,
        "epc_rating": "B",
        "epc_score": 87,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 2018,
        "consumer_unit": "Hager JN112BC 12-way RCBO board",
        "gas_appliances": [
            {"type": "System Boiler", "make_model": "Worcester Bosch Greenstar 8000 Life 40kW", "location": "Utility Room", "flue_type": "Balanced flue"},
            {"type": "Gas Hob", "make_model": "Siemens EC6A5PB90", "location": "Kitchen", "flue_type": "N/A"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "fifth_avenue": {
        "key": "fifth_avenue",
        "address": "62 Fifth Avenue",
        "city": "Harlow",
        "postcode": "CM20 2LQ",
        "property_type": "2-bed flat",
        "furnished": "Partly furnished",
        "monthly_rent": 950.00,
        "landlord_key": "mensah",
        "agent_key": "haart",
        "num_bedrooms": 2,
        "epc_rating": "D",
        "epc_score": 61,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 2001,
        "consumer_unit": "MK Sentry 10-way split load",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Ideal Logic+ Combi C24", "location": "Kitchen cupboard", "flue_type": "Balanced flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "commonside_road": {
        "key": "commonside_road",
        "address": "55 Commonside Road",
        "city": "Harlow",
        "postcode": "CM18 6YH",
        "property_type": "3-bed detached",
        "furnished": "Unfurnished",
        "monthly_rent": 1550.00,
        "landlord_key": "mensah",
        "agent_key": "leaders",
        "num_bedrooms": 3,
        "epc_rating": "C",
        "epc_score": 78,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 2004,
        "consumer_unit": "Schneider Electric REARO16S 16-way",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Baxi 800 Combi 2 33kW", "location": "Kitchen", "flue_type": "Balanced flue"},
            {"type": "Gas Hob", "make_model": "AEG HKB65410NB", "location": "Kitchen", "flue_type": "N/A"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "northgate_end": {
        "key": "northgate_end",
        "address": "3 Northgate End",
        "city": "Bishop's Stortford",
        "postcode": "CM23 2ET",
        "property_type": "1-bed flat",
        "furnished": "Furnished",
        "monthly_rent": 875.00,
        "landlord_key": "webb",
        "agent_key": "geoffrey_matthew",
        "num_bedrooms": 1,
        "epc_rating": "E",
        "epc_score": 44,
        "eicr_result": "Satisfactory",
        "eicr_observations": [
            {"item": "1", "description": "No supplementary bonding in bathroom — older installation, pre-17th edition", "code": "C3", "location": "Bathroom"},
        ],
        "installation_age": 1983,
        "consumer_unit": "Crabtree Loadmaster 8-way",
        "gas_appliances": [
            {"type": "Combination Boiler", "make_model": "Potterton Titanium 28 HE", "location": "Kitchen", "flue_type": "Balanced flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "bell_street": {
        "key": "bell_street",
        "address": "11 Bell Street",
        "city": "Sawbridgeworth",
        "postcode": "CM21 9AN",
        "property_type": "2-bed terraced house",
        "furnished": "Unfurnished",
        "monthly_rent": 1125.00,
        "landlord_key": "obrien",
        "agent_key": "intercounty",
        "num_bedrooms": 2,
        "epc_rating": "D",
        "epc_score": 65,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 2002,
        "consumer_unit": "Legrand 4 162 13 14-way",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Glow-worm Energy 25C", "location": "Kitchen", "flue_type": "Balanced flue"},
            {"type": "Gas Hob", "make_model": "Beko HIZG32120S", "location": "Kitchen", "flue_type": "N/A"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "london_road_hoddesdon": {
        "key": "london_road_hoddesdon",
        "address": "78 London Road",
        "city": "Hoddesdon",
        "postcode": "EN11 8JL",
        "property_type": "3-bed semi-detached",
        "furnished": "Unfurnished",
        "monthly_rent": 1400.00,
        "landlord_key": "petrov",
        "agent_key": "kings_group",
        "num_bedrooms": 3,
        "epc_rating": "D",
        "epc_score": 58,
        "eicr_result": "Satisfactory",
        "eicr_observations": [
            {"item": "1", "description": "Presence of aluminium wiring — periodic review recommended", "code": "FI", "location": "Upstairs ring circuit"},
        ],
        "installation_age": 1976,
        "consumer_unit": "Hager VML912CPD 12-way",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Viessmann Vitodens 100-W 26kW", "location": "Utility room", "flue_type": "Balanced flue"},
            {"type": "Gas Hob", "make_model": "Hotpoint GC750TIX", "location": "Kitchen", "flue_type": "N/A"},
            {"type": "Gas Fire", "make_model": "Gazco Logic HE Slimline", "location": "Sitting Room", "flue_type": "Balanced flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "high_street_epping": {
        "key": "high_street_epping",
        "address": "22 High Street",
        "city": "Epping",
        "postcode": "CM16 4DA",
        "property_type": "2-bed flat",
        "furnished": "Furnished",
        "monthly_rent": 1050.00,
        "landlord_key": "chen",
        "agent_key": "intercounty",
        "num_bedrooms": 2,
        "epc_rating": "C",
        "epc_score": 72,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 2013,
        "consumer_unit": "Hager JN212BC 12-way RCBO board",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Worcester Bosch Greenstar CDi Classic 30", "location": "Bathroom cupboard", "flue_type": "Balanced flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
    "kitson_way": {
        "key": "kitson_way",
        "address": "8 Kitson Way",
        "city": "Harlow",
        "postcode": "CM20 1DQ",
        "property_type": "1-bed flat",
        "furnished": "Furnished",
        "monthly_rent": 795.00,
        "landlord_key": "chen",
        "agent_key": "future_let",
        "num_bedrooms": 1,
        "epc_rating": "B",
        "epc_score": 83,
        "eicr_result": "Satisfactory",
        "eicr_observations": [],
        "installation_age": 2020,
        "consumer_unit": "Hager JN110BC 10-way RCBO board",
        "gas_appliances": [
            {"type": "Combi Boiler", "make_model": "Ideal Logic Max C24", "location": "Hallway cupboard", "flue_type": "Balanced flue"},
        ],
        "gas_result": "PASS",
        "gas_defects": None,
        "gas_warnings": None,
    },
}


# ---------------------------------------------------------------------------
# 5. TENANCIES — maps tenants to properties with financial and legal details
# ---------------------------------------------------------------------------

TENANCIES = {
    "mandarin_drive": {
        "property_key": "mandarin_drive",
        "tenant_keys": ["sharma_r"],
        "start_date": datetime.date(2023, 3, 1),
        "end_date": datetime.date(2024, 2, 29),
        "deposit_amount": 1326.92,
        "deposit_scheme": "DPS",
        "deposit_ref": "DPS230301SH4471K",
        "agent_key": "belvoir",
        "rent_review_date": datetime.date(2024, 3, 1),
        "tenancy_type": "AST",
    },
    "barn_mead": {
        "property_key": "barn_mead",
        "tenant_keys": ["williams_k"],
        "start_date": datetime.date(2022, 9, 15),
        "end_date": datetime.date(2023, 9, 14),
        "deposit_amount": 952.50,
        "deposit_scheme": "MyDeposits",
        "deposit_ref": "MYD-22-00391-W",
        "agent_key": "future_let",
        "rent_review_date": datetime.date(2023, 9, 15),
        "tenancy_type": "AST",
    },
    "gilden_way": {
        "property_key": "gilden_way",
        "tenant_keys": ["kowalski_t", "kowalski_a"],
        "start_date": datetime.date(2023, 7, 1),
        "end_date": datetime.date(2024, 6, 30),
        "deposit_amount": 1557.69,
        "deposit_scheme": "TDS",
        "deposit_ref": "TDS2307-GL-0081",
        "agent_key": "haart",
        "rent_review_date": datetime.date(2024, 7, 1),
        "tenancy_type": "AST",
    },
    "parndon_mill": {
        "property_key": "parndon_mill",
        "tenant_keys": ["adeyemi_j"],
        "start_date": datetime.date(2024, 1, 20),
        "end_date": datetime.date(2025, 1, 19),
        "deposit_amount": 750.00,
        "deposit_scheme": "DPS",
        "deposit_ref": "DPS240120AJ8812P",
        "agent_key": "belvoir",
        "rent_review_date": datetime.date(2025, 1, 20),
        "tenancy_type": "AST",
    },
    "fennells": {
        "property_key": "fennells",
        "tenant_keys": ["patel_n", "patel_v"],
        "start_date": datetime.date(2023, 5, 1),
        "end_date": datetime.date(2024, 4, 30),
        "deposit_amount": 1125.00,
        "deposit_scheme": "MyDeposits",
        "deposit_ref": "MYD-23-00814-NP",
        "agent_key": "leaders",
        "rent_review_date": datetime.date(2024, 5, 1),
        "tenancy_type": "AST",
    },
    "abbotsweld": {
        "property_key": "abbotsweld",
        "tenant_keys": ["singh_h"],
        "start_date": datetime.date(2022, 11, 1),
        "end_date": datetime.date(2023, 10, 31),
        "deposit_amount": 1471.15,
        "deposit_scheme": "TDS",
        "deposit_ref": "TDS2211-AB-0034",
        "agent_key": None,
        "rent_review_date": datetime.date(2023, 11, 1),
        "tenancy_type": "AST",
    },
    "maddox_road": {
        "property_key": "maddox_road",
        "tenant_keys": ["murphy_c"],
        "start_date": datetime.date(2023, 10, 1),
        "end_date": datetime.date(2024, 9, 30),
        "deposit_amount": 1264.23,
        "deposit_scheme": "DPS",
        "deposit_ref": "DPS231001CM0091R",
        "agent_key": "kings_group",
        "rent_review_date": datetime.date(2024, 10, 1),
        "tenancy_type": "AST",
    },
    "potter_street": {
        "property_key": "potter_street",
        "tenant_keys": ["nguyen_p"],
        "start_date": datetime.date(2024, 3, 15),
        "end_date": datetime.date(2025, 3, 14),
        "deposit_amount": 2076.92,
        "deposit_scheme": "MyDeposits",
        "deposit_ref": "MYD-24-00220-PN",
        "agent_key": "belvoir",
        "rent_review_date": datetime.date(2025, 3, 15),
        "tenancy_type": "AST",
    },
    "fifth_avenue": {
        "property_key": "fifth_avenue",
        "tenant_keys": ["ali_s"],
        "start_date": datetime.date(2023, 8, 1),
        "end_date": datetime.date(2024, 7, 31),
        "deposit_amount": 1096.15,
        "deposit_scheme": "DPS",
        "deposit_ref": "DPS230801SA5533K",
        "agent_key": "haart",
        "rent_review_date": datetime.date(2024, 8, 1),
        "tenancy_type": "AST",
    },
    "commonside_road": {
        "property_key": "commonside_road",
        "tenant_keys": ["jones_m", "jones_e"],
        "start_date": datetime.date(2023, 6, 15),
        "end_date": datetime.date(2024, 6, 14),
        "deposit_amount": 1788.46,
        "deposit_scheme": "TDS",
        "deposit_ref": "TDS2306-CR-0055",
        "agent_key": "leaders",
        "rent_review_date": datetime.date(2024, 6, 15),
        "tenancy_type": "AST",
    },
    "northgate_end": {
        "property_key": "northgate_end",
        "tenant_keys": ["nowak_f"],
        "start_date": datetime.date(2024, 2, 1),
        "end_date": datetime.date(2025, 1, 31),
        "deposit_amount": 1009.62,
        "deposit_scheme": "MyDeposits",
        "deposit_ref": "MYD-24-00088-FN",
        "agent_key": "geoffrey_matthew",
        "rent_review_date": datetime.date(2025, 2, 1),
        "tenancy_type": "AST",
    },
    "bell_street": {
        "property_key": "bell_street",
        "tenant_keys": ["singh_a"],
        "start_date": datetime.date(2023, 4, 1),
        "end_date": datetime.date(2024, 3, 31),
        "deposit_amount": 1298.08,
        "deposit_scheme": "DPS",
        "deposit_ref": "DPS230401AS7712B",
        "agent_key": "intercounty",
        "rent_review_date": datetime.date(2024, 4, 1),
        "tenancy_type": "AST",
    },
    "london_road_hoddesdon": {
        "property_key": "london_road_hoddesdon",
        "tenant_keys": ["thompson_g"],
        "start_date": datetime.date(2023, 9, 1),
        "end_date": datetime.date(2024, 8, 31),
        "deposit_amount": 1615.38,
        "deposit_scheme": "TDS",
        "deposit_ref": "TDS2309-LH-0099",
        "agent_key": "kings_group",
        "rent_review_date": datetime.date(2024, 9, 1),
        "tenancy_type": "AST",
    },
    "high_street_epping": {
        "property_key": "high_street_epping",
        "tenant_keys": ["osei_k"],
        "start_date": datetime.date(2024, 4, 1),
        "end_date": datetime.date(2025, 3, 31),
        "deposit_amount": 1211.54,
        "deposit_scheme": "MyDeposits",
        "deposit_ref": "MYD-24-00315-KO",
        "agent_key": "intercounty",
        "rent_review_date": datetime.date(2025, 4, 1),
        "tenancy_type": "AST",
    },
    "kitson_way": {
        "property_key": "kitson_way",
        "tenant_keys": ["hassan_z"],
        "start_date": datetime.date(2024, 5, 1),
        "end_date": datetime.date(2025, 4, 30),
        "deposit_amount": 917.31,
        "deposit_scheme": "DPS",
        "deposit_ref": "DPS240501ZH3341K",
        "agent_key": "future_let",
        "rent_review_date": datetime.date(2025, 5, 1),
        "tenancy_type": "AST",
    },
}


# ---------------------------------------------------------------------------
# 6. GAS SAFE ENGINEERS (4)
# ---------------------------------------------------------------------------

GAS_ENGINEERS = {
    "fletcher": {
        "key": "fletcher",
        "name": "Mr. Brian Fletcher",
        "company": "Fletcher Gas Services",
        "gas_safe_number": "512847",
        "phone": "07734 221 908",
        "address": "6 Broadfield, Harlow, Essex, CM20 3PB",
        "email": "brian@fletchergas.co.uk",
    },
    "iqbal": {
        "key": "iqbal",
        "name": "Mr. Tariq Iqbal",
        "company": "TI Heating & Gas Ltd",
        "gas_safe_number": "608391",
        "phone": "07819 554 177",
        "address": "23 Hazel Lane, Harlow, Essex, CM17 0FT",
        "email": "tariq@ti-heating.co.uk",
    },
    "mcallister": {
        "key": "mcallister",
        "name": "Ms. Donna McAllister",
        "company": "Essex Heating Solutions",
        "gas_safe_number": "734026",
        "phone": "07622 003 815",
        "address": "41 Tawneys Road, Harlow, Essex, CM18 6SN",
        "email": "donna@essexheatingsolutions.co.uk",
    },
    "okafor": {
        "key": "okafor",
        "name": "Mr. Chidi Okafor",
        "company": "Okafor Plumbing & Gas",
        "gas_safe_number": "891234",
        "phone": "07944 779 002",
        "address": "9 Burnt Mill, Harlow, Essex, CM20 2HS",
        "email": "chidi@okaforgas.co.uk",
    },
}

# Assign each property a gas engineer
PROPERTY_GAS_ENGINEER = {
    "mandarin_drive": "fletcher",
    "barn_mead": "iqbal",
    "gilden_way": "mcallister",
    "parndon_mill": "fletcher",
    "fennells": "iqbal",
    "abbotsweld": "okafor",
    "maddox_road": "mcallister",
    "potter_street": "fletcher",
    "fifth_avenue": "iqbal",
    "commonside_road": "okafor",
    "northgate_end": "mcallister",
    "bell_street": "iqbal",
    "london_road_hoddesdon": "okafor",
    "high_street_epping": "fletcher",
    "kitson_way": "mcallister",
}

# Gas safety inspection dates (within ~12 months of tenancy start)
GAS_INSPECTION_DATES = {
    "mandarin_drive": datetime.date(2023, 2, 14),
    "barn_mead": datetime.date(2022, 9, 1),
    "gilden_way": datetime.date(2023, 6, 19),
    "parndon_mill": datetime.date(2024, 1, 8),
    "fennells": datetime.date(2023, 4, 21),
    "abbotsweld": datetime.date(2022, 10, 17),
    "maddox_road": datetime.date(2023, 9, 22),
    "potter_street": datetime.date(2024, 3, 4),
    "fifth_avenue": datetime.date(2023, 7, 25),
    "commonside_road": datetime.date(2023, 6, 3),
    "northgate_end": datetime.date(2024, 1, 22),
    "bell_street": datetime.date(2023, 3, 14),
    "london_road_hoddesdon": datetime.date(2023, 8, 28),
    "high_street_epping": datetime.date(2024, 3, 19),
    "kitson_way": datetime.date(2024, 4, 24),
}


# ---------------------------------------------------------------------------
# 7. ELECTRICIANS (3)
# ---------------------------------------------------------------------------

ELECTRICIANS = {
    "harris": {
        "key": "harris",
        "name": "Mr. Steve Harris",
        "company": "Harris Electrical Contractors Ltd",
        "registration_body": "NICEIC",
        "registration_number": "NIC-52341-E",
        "phone": "07711 883 240",
        "address": "17 Haydens Road, Harlow, Essex, CM19 5BB",
        "email": "steve@harriselectrical.co.uk",
    },
    "dabrowski": {
        "key": "dabrowski",
        "name": "Mr. Piotr Dabrowski",
        "company": "PD Electrical Solutions",
        "registration_body": "NAPIT",
        "registration_number": "NAP-61008-PD",
        "phone": "07823 441 669",
        "address": "3 Berecroft, Harlow, Essex, CM18 7AB",
        "email": "piotr@pd-electrical.co.uk",
    },
    "campbell": {
        "key": "campbell",
        "name": "Ms. Ruth Campbell",
        "company": "Campbell Electrical Services",
        "registration_body": "ELECSA",
        "registration_number": "ELS-39812-RC",
        "phone": "07500 227 814",
        "address": "52 Shepherds Bush, Harlow, Essex, CM20 1HB",
        "email": "ruth@campbellelectrical.co.uk",
    },
}

PROPERTY_ELECTRICIAN = {
    "mandarin_drive": "harris",
    "barn_mead": "dabrowski",
    "gilden_way": "campbell",
    "parndon_mill": "harris",
    "fennells": "dabrowski",
    "abbotsweld": "campbell",
    "maddox_road": "harris",
    "potter_street": "dabrowski",
    "fifth_avenue": "campbell",
    "commonside_road": "harris",
    "northgate_end": "dabrowski",
    "bell_street": "campbell",
    "london_road_hoddesdon": "harris",
    "high_street_epping": "dabrowski",
    "kitson_way": "campbell",
}

EICR_INSPECTION_DATES = {
    "mandarin_drive": datetime.date(2022, 11, 9),
    "barn_mead": datetime.date(2022, 8, 3),
    "gilden_way": datetime.date(2023, 5, 12),
    "parndon_mill": datetime.date(2023, 11, 6),
    "fennells": datetime.date(2023, 3, 28),
    "abbotsweld": datetime.date(2022, 10, 4),
    "maddox_road": datetime.date(2023, 8, 16),
    "potter_street": datetime.date(2024, 2, 22),
    "fifth_avenue": datetime.date(2023, 6, 17),
    "commonside_road": datetime.date(2023, 4, 5),
    "northgate_end": datetime.date(2023, 12, 11),
    "bell_street": datetime.date(2023, 2, 8),
    "london_road_hoddesdon": datetime.date(2023, 7, 19),
    "high_street_epping": datetime.date(2024, 2, 13),
    "kitson_way": datetime.date(2024, 4, 2),
}


# ---------------------------------------------------------------------------
# 8. EPC ASSESSORS (2)
# ---------------------------------------------------------------------------

EPC_ASSESSORS = {
    "richardson": {
        "key": "richardson",
        "name": "Mr. Paul Richardson",
        "assessor_number": "ECMK004821",
        "accreditation_scheme": "Elmhurst Energy",
        "phone": "07760 119 342",
        "email": "paul.richardson@epcassess.co.uk",
    },
    "yeung": {
        "key": "yeung",
        "name": "Ms. Angela Yeung",
        "assessor_number": "QUIDOS008813",
        "accreditation_scheme": "Quidos",
        "phone": "07831 664 097",
        "email": "angela.yeung@energycheck.co.uk",
    },
}

PROPERTY_EPC_ASSESSOR = {
    "mandarin_drive": "richardson",
    "barn_mead": "yeung",
    "gilden_way": "richardson",
    "parndon_mill": "yeung",
    "fennells": "richardson",
    "abbotsweld": "yeung",
    "maddox_road": "richardson",
    "potter_street": "yeung",
    "fifth_avenue": "richardson",
    "commonside_road": "yeung",
    "northgate_end": "richardson",
    "bell_street": "yeung",
    "london_road_hoddesdon": "richardson",
    "high_street_epping": "yeung",
    "kitson_way": "richardson",
}

EPC_INSPECTION_DATES = {
    "mandarin_drive": datetime.date(2022, 10, 3),
    "barn_mead": datetime.date(2022, 7, 14),
    "gilden_way": datetime.date(2022, 12, 5),
    "parndon_mill": datetime.date(2023, 8, 22),
    "fennells": datetime.date(2023, 1, 17),
    "abbotsweld": datetime.date(2021, 9, 8),
    "maddox_road": datetime.date(2023, 6, 30),
    "potter_street": datetime.date(2023, 11, 1),
    "fifth_avenue": datetime.date(2022, 5, 19),
    "commonside_road": datetime.date(2023, 2, 28),
    "northgate_end": datetime.date(2022, 3, 10),
    "bell_street": datetime.date(2022, 11, 21),
    "london_road_hoddesdon": datetime.date(2023, 4, 14),
    "high_street_epping": datetime.date(2023, 12, 7),
    "kitson_way": datetime.date(2024, 3, 18),
}

# EPC feature table data: Feature -> (Description, Rating)
# Rating: 1=Very Poor, 2=Poor, 3=Average, 4=Good, 5=Very Good
EPC_FEATURES = {
    "mandarin_drive": [
        ("Walls", "Cavity wall, as built, no insulation (assumed)", "Poor"),
        ("Roof", "Pitched, 100mm loft insulation", "Average"),
        ("Floor", "Suspended timber, no insulation (assumed)", "Poor"),
        ("Windows", "Double glazed (uPVC), installed 2002", "Average"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Programmer and room thermostat", "Average"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From main system boiler", "Good"),
        ("Lighting", "Low energy lighting in 50% of fixed outlets", "Average"),
    ],
    "barn_mead": [
        ("Walls", "Cavity wall, filled, as built", "Good"),
        ("Roof", "Flat roof, 150mm insulation", "Good"),
        ("Floor", "Solid concrete, no insulation (assumed)", "Average"),
        ("Windows", "Double glazed (uPVC), 2007", "Good"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Time and temperature zone control", "Very Good"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Good"),
        ("Lighting", "Low energy lighting in all fixed outlets", "Very Good"),
    ],
    "gilden_way": [
        ("Walls", "Cavity wall, as built, no insulation (assumed)", "Poor"),
        ("Roof", "Pitched, 50mm loft insulation", "Poor"),
        ("Floor", "Suspended timber, no insulation (assumed)", "Poor"),
        ("Windows", "Single glazed", "Very Poor"),
        ("Main heating", "Boiler and radiators, mains gas", "Average"),
        ("Main heat control", "Programmer and room thermostat", "Average"),
        ("Secondary heating", "Room heaters, mains gas", "Poor"),
        ("Hot water", "From main system boiler", "Average"),
        ("Lighting", "Low energy lighting in 25% of fixed outlets", "Poor"),
    ],
    "parndon_mill": [
        ("Walls", "Solid brick, as built, no insulation", "Very Poor"),
        ("Roof", "Flat roof, no insulation (assumed)", "Very Poor"),
        ("Floor", "Solid concrete, no insulation (assumed)", "Poor"),
        ("Windows", "Single glazed", "Very Poor"),
        ("Main heating", "Back boiler to radiators, mains gas", "Average"),
        ("Main heat control", "Programmer only", "Poor"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From back boiler", "Average"),
        ("Lighting", "Low energy lighting in 10% of fixed outlets", "Very Poor"),
    ],
    "fennells": [
        ("Walls", "Cavity wall, filled", "Good"),
        ("Roof", "Pitched, 250mm loft insulation", "Very Good"),
        ("Floor", "Solid concrete, insulated", "Good"),
        ("Windows", "Double glazed (uPVC), 2010", "Good"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Time and temperature zone control", "Very Good"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Good"),
        ("Lighting", "Low energy lighting in 75% of fixed outlets", "Good"),
    ],
    "abbotsweld": [
        ("Walls", "Solid brick, 100mm external insulation", "Average"),
        ("Roof", "Pitched, 50mm loft insulation", "Poor"),
        ("Floor", "Suspended timber, no insulation (assumed)", "Very Poor"),
        ("Windows", "Single glazed (original timber frames)", "Very Poor"),
        ("Main heating", "Boiler and radiators, mains gas", "Poor"),
        ("Main heat control", "Programmer only", "Very Poor"),
        ("Secondary heating", "Room heaters, mains gas", "Very Poor"),
        ("Hot water", "From main system boiler", "Poor"),
        ("Lighting", "Low energy lighting in 10% of fixed outlets", "Very Poor"),
    ],
    "maddox_road": [
        ("Walls", "Cavity wall, filled, 1999", "Average"),
        ("Roof", "Pitched, 100mm loft insulation", "Average"),
        ("Floor", "Solid concrete, no insulation", "Poor"),
        ("Windows", "Double glazed (uPVC), 1999", "Average"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Programmer and room thermostat", "Average"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Good"),
        ("Lighting", "Low energy lighting in 50% of fixed outlets", "Average"),
    ],
    "potter_street": [
        ("Walls", "Cavity wall, filled, 2018", "Very Good"),
        ("Roof", "Pitched, 300mm loft insulation", "Very Good"),
        ("Floor", "Solid concrete, insulated", "Very Good"),
        ("Windows", "Double glazed (high performance), 2018", "Very Good"),
        ("Main heating", "Boiler and radiators, mains gas", "Very Good"),
        ("Main heat control", "Time and temperature zone control", "Very Good"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From system boiler", "Very Good"),
        ("Lighting", "Low energy lighting in all fixed outlets", "Very Good"),
    ],
    "fifth_avenue": [
        ("Walls", "Cavity wall, filled", "Good"),
        ("Roof", "Flat roof, 100mm insulation", "Average"),
        ("Floor", "Solid concrete, no insulation", "Poor"),
        ("Windows", "Double glazed (uPVC), 2001", "Average"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Programmer and room thermostat", "Average"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Good"),
        ("Lighting", "Low energy lighting in 50% of fixed outlets", "Average"),
    ],
    "commonside_road": [
        ("Walls", "Cavity wall, filled", "Good"),
        ("Roof", "Pitched, 270mm loft insulation", "Very Good"),
        ("Floor", "Solid concrete, insulated", "Good"),
        ("Windows", "Double glazed (uPVC), 2004", "Good"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Time and temperature zone control", "Very Good"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Good"),
        ("Lighting", "Low energy lighting in 75% of fixed outlets", "Good"),
    ],
    "northgate_end": [
        ("Walls", "Solid brick, no insulation (assumed)", "Poor"),
        ("Roof", "Pitched, 75mm loft insulation", "Poor"),
        ("Floor", "Suspended timber, no insulation (assumed)", "Poor"),
        ("Windows", "Double glazed (uPVC), 2004", "Average"),
        ("Main heating", "Boiler and radiators, mains gas", "Average"),
        ("Main heat control", "Programmer only", "Poor"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Average"),
        ("Lighting", "Low energy lighting in 25% of fixed outlets", "Poor"),
    ],
    "bell_street": [
        ("Walls", "Cavity wall, filled, 2002", "Good"),
        ("Roof", "Pitched, 150mm loft insulation", "Good"),
        ("Floor", "Solid concrete, no insulation", "Poor"),
        ("Windows", "Double glazed (uPVC), 2002", "Good"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Programmer and room thermostat", "Average"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Good"),
        ("Lighting", "Low energy lighting in 50% of fixed outlets", "Average"),
    ],
    "london_road_hoddesdon": [
        ("Walls", "Cavity wall, as built, no insulation (assumed)", "Poor"),
        ("Roof", "Pitched, 100mm loft insulation", "Average"),
        ("Floor", "Suspended timber, no insulation (assumed)", "Poor"),
        ("Windows", "Double glazed (uPVC), 2005", "Average"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Programmer and room thermostat", "Average"),
        ("Secondary heating", "Room heater, mains gas", "Average"),
        ("Hot water", "From main system boiler", "Good"),
        ("Lighting", "Low energy lighting in 25% of fixed outlets", "Poor"),
    ],
    "high_street_epping": [
        ("Walls", "Cavity wall, filled", "Good"),
        ("Roof", "Flat roof, 150mm insulation", "Good"),
        ("Floor", "Solid concrete, insulated (2013)", "Good"),
        ("Windows", "Double glazed (uPVC), 2013", "Good"),
        ("Main heating", "Boiler and radiators, mains gas", "Good"),
        ("Main heat control", "Time and temperature zone control", "Very Good"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Good"),
        ("Lighting", "Low energy lighting in 75% of fixed outlets", "Good"),
    ],
    "kitson_way": [
        ("Walls", "Cavity wall, filled, 2020", "Very Good"),
        ("Roof", "Pitched, 300mm loft insulation", "Very Good"),
        ("Floor", "Solid concrete, insulated", "Very Good"),
        ("Windows", "Triple glazed, 2020", "Very Good"),
        ("Main heating", "Boiler and radiators, mains gas", "Very Good"),
        ("Main heat control", "Time and temperature zone control", "Very Good"),
        ("Secondary heating", "None", "N/A"),
        ("Hot water", "From combination boiler", "Very Good"),
        ("Lighting", "Low energy lighting in all fixed outlets", "Very Good"),
    ],
}


# ---------------------------------------------------------------------------
# 9. INVENTORY CLERKS (2)
# ---------------------------------------------------------------------------

INVENTORY_CLERKS = {
    "baxter": {
        "key": "baxter",
        "name": "Mr. Colin Baxter",
        "company": "Harlow Inventory Services",
        "phone": "07752 338 901",
        "email": "colin@harlowinventory.co.uk",
    },
    "afolabi": {
        "key": "afolabi",
        "name": "Ms. Tola Afolabi",
        "company": "Essex Property Inventories Ltd",
        "phone": "07919 221 634",
        "email": "tola@essexinventories.co.uk",
    },
}

PROPERTY_INVENTORY_CLERK = {
    "mandarin_drive": "baxter",
    "barn_mead": "afolabi",
    "gilden_way": "baxter",
    "parndon_mill": "afolabi",
    "fennells": "baxter",
    "abbotsweld": "afolabi",
    "maddox_road": "baxter",
    "potter_street": "afolabi",
    "fifth_avenue": "baxter",
    "commonside_road": "afolabi",
    "northgate_end": "baxter",
    "bell_street": "afolabi",
    "london_road_hoddesdon": "baxter",
    "high_street_epping": "afolabi",
    "kitson_way": "baxter",
}

INVENTORY_DATES = {
    "mandarin_drive": datetime.date(2023, 2, 28),
    "barn_mead": datetime.date(2022, 9, 14),
    "gilden_way": datetime.date(2023, 6, 30),
    "parndon_mill": datetime.date(2024, 1, 19),
    "fennells": datetime.date(2023, 4, 30),
    "abbotsweld": datetime.date(2022, 10, 31),
    "maddox_road": datetime.date(2023, 9, 30),
    "potter_street": datetime.date(2024, 3, 14),
    "fifth_avenue": datetime.date(2023, 7, 31),
    "commonside_road": datetime.date(2023, 6, 14),
    "northgate_end": datetime.date(2024, 1, 31),
    "bell_street": datetime.date(2023, 3, 31),
    "london_road_hoddesdon": datetime.date(2023, 8, 31),
    "high_street_epping": datetime.date(2024, 3, 31),
    "kitson_way": datetime.date(2024, 4, 30),
}


# ---------------------------------------------------------------------------
# 10. CONTRACTORS (3 — maintenance)
# ---------------------------------------------------------------------------

CONTRACTORS = {
    "riley_plumbing": {
        "key": "riley_plumbing",
        "name": "Mr. Sean Riley",
        "company": "Riley Plumbing & Heating",
        "trade": "Plumber",
        "phone": "07788 441 221",
        "email": "sean@rileyplumbing.co.uk",
        "address": "25 Pyenest Road, Harlow, Essex, CM18 7PB",
    },
    "axis_builders": {
        "key": "axis_builders",
        "name": "Mr. Derek Owusu",
        "company": "Axis Property Maintenance",
        "trade": "General Builder",
        "phone": "07866 223 990",
        "email": "derek@axismaintenance.co.uk",
        "address": "7 Trotters Road, Harlow, Essex, CM20 1LB",
    },
    "lockfast": {
        "key": "lockfast",
        "name": "Mr. Ivan Horak",
        "company": "Lockfast Security Solutions",
        "trade": "Locksmith",
        "phone": "07711 009 338",
        "email": "ivan@lockfast.co.uk",
        "address": "14 Bush Fair, Harlow, Essex, CM18 6LY",
    },
}


# ---------------------------------------------------------------------------
# 11. METER SERIAL NUMBERS (for inventories / check-in reports)
# ---------------------------------------------------------------------------

METER_SERIALS = {
    "mandarin_drive": {"electric": "J00K3184211", "gas": "G4407821033"},
    "barn_mead": {"electric": "E44M7711020", "gas": "G1109934412"},
    "gilden_way": {"electric": "J22A5530847", "gas": "G8821105599"},
    "parndon_mill": {"electric": "E17B0098331", "gas": "G3344182200"},
    "fennells": {"electric": "J88C4421199", "gas": "G5512904437"},
    "abbotsweld": {"electric": "E03D7814002", "gas": "G7780013341"},
    "maddox_road": {"electric": "J56E2209918", "gas": "G9921440018"},
    "potter_street": {"electric": "E91F8813374", "gas": "G6603781121"},
    "fifth_avenue": {"electric": "J34G1107742", "gas": "G4492018853"},
    "commonside_road": {"electric": "E78H4450019", "gas": "G1137289944"},
    "northgate_end": {"electric": "J12I9920003", "gas": "G8833561108"},
    "bell_street": {"electric": "E55J3381174", "gas": "G2219048875"},
    "london_road_hoddesdon": {"electric": "J99K1140228", "gas": "G5567312290"},
    "high_street_epping": {"electric": "E40L8823349", "gas": "G3348891130"},
    "kitson_way": {"electric": "J77M2204415", "gas": "G7714562203"},
}

# Initial meter readings at tenancy start
METER_READINGS = {
    "mandarin_drive": {"electric": 14832, "gas": 3041},
    "barn_mead": {"electric": 8871, "gas": 1122},
    "gilden_way": {"electric": 22140, "gas": 7783},
    "parndon_mill": {"electric": 3310, "gas": 994},
    "fennells": {"electric": 11002, "gas": 2891},
    "abbotsweld": {"electric": 31458, "gas": 14022},
    "maddox_road": {"electric": 19003, "gas": 6401},
    "potter_street": {"electric": 6720, "gas": 1884},
    "fifth_avenue": {"electric": 13390, "gas": 4103},
    "commonside_road": {"electric": 8001, "gas": 2330},
    "northgate_end": {"electric": 25441, "gas": 9871},
    "bell_street": {"electric": 17821, "gas": 5642},
    "london_road_hoddesdon": {"electric": 28993, "gas": 11230},
    "high_street_epping": {"electric": 4551, "gas": 1034},
    "kitson_way": {"electric": 1130, "gas": 228},
}


# ---------------------------------------------------------------------------
# 12. HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def get_property(key):
    """Return property dict by key string (e.g. 'mandarin_drive')"""
    return PROPERTIES.get(key)


def get_landlord_for_property(property_key):
    """Return landlord dict for a given property"""
    prop = PROPERTIES.get(property_key)
    if not prop:
        return None
    return LANDLORDS.get(prop["landlord_key"])


def get_tenants_for_property(property_key):
    """Return list of tenant dicts for a given property"""
    tenancy = TENANCIES.get(property_key)
    if not tenancy:
        return []
    return [TENANTS[k] for k in tenancy["tenant_keys"] if k in TENANTS]


def get_tenancy_for_property(property_key):
    """Return tenancy details (dates, deposit, scheme, rent) for a property"""
    tenancy = TENANCIES.get(property_key)
    if not tenancy:
        return None
    prop = PROPERTIES.get(property_key)
    result = dict(tenancy)
    if prop:
        result["monthly_rent"] = prop["monthly_rent"]
    return result


def get_agent_for_property(property_key):
    """Return agent dict or None if self-managed"""
    prop = PROPERTIES.get(property_key)
    if not prop:
        return None
    if prop["agent_key"] is None:
        return None
    return AGENCIES.get(prop["agent_key"])


def get_gas_engineer_for_property(property_key):
    """Return gas engineer dict for a given property"""
    engineer_key = PROPERTY_GAS_ENGINEER.get(property_key)
    return GAS_ENGINEERS.get(engineer_key) if engineer_key else None


def get_electrician_for_property(property_key):
    """Return electrician dict for a given property"""
    elec_key = PROPERTY_ELECTRICIAN.get(property_key)
    return ELECTRICIANS.get(elec_key) if elec_key else None


def get_epc_assessor_for_property(property_key):
    """Return EPC assessor dict for a given property"""
    assessor_key = PROPERTY_EPC_ASSESSOR.get(property_key)
    return EPC_ASSESSORS.get(assessor_key) if assessor_key else None


def get_inventory_clerk_for_property(property_key):
    """Return inventory clerk dict for a given property"""
    clerk_key = PROPERTY_INVENTORY_CLERK.get(property_key)
    return INVENTORY_CLERKS.get(clerk_key) if clerk_key else None


def get_all_property_keys():
    """Return sorted list of all property keys"""
    return sorted(PROPERTIES.keys())


# ---------------------------------------------------------------------------
# QUICK SELF-TEST (run data.py directly to check for errors)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Properties loaded:  {len(PROPERTIES)}")
    print(f"Landlords loaded:   {len(LANDLORDS)}")
    print(f"Tenants loaded:     {len(TENANTS)}")
    print(f"Tenancies loaded:   {len(TENANCIES)}")
    print(f"Agencies loaded:    {len(AGENCIES)}")
    print(f"Gas engineers:      {len(GAS_ENGINEERS)}")
    print(f"Electricians:       {len(ELECTRICIANS)}")
    print(f"EPC assessors:      {len(EPC_ASSESSORS)}")
    print(f"Inventory clerks:   {len(INVENTORY_CLERKS)}")
    print(f"Contractors:        {len(CONTRACTORS)}")
    print()
    for pk in get_all_property_keys():
        prop = get_property(pk)
        landlord = get_landlord_for_property(pk)
        tenants = get_tenants_for_property(pk)
        agent = get_agent_for_property(pk)
        tenancy = get_tenancy_for_property(pk)
        print(
            f"  {pk:<30} | {prop['address']:<35} | "
            f"EPC:{prop['epc_rating']}({prop['epc_score']}) | "
            f"EICR:{prop['eicr_result']:<14} | "
            f"Gas:{prop['gas_result']} | "
            f"Landlord:{landlord['last_name']:<12} | "
            f"Agent:{agent['name'] if agent else 'Self-managed'}"
        )
