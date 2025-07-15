import os
import time
from dotenv import load_dotenv
import json
import google.generativeai as genai
import PIL.Image




try:
    # Load the API key from environment variables
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(env_path)
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    print("FATAL ERROR: 'GOOGLE_API_KEY' environment variable not set.")
    print("Please set it before running the script.")
    exit()
model = genai.GenerativeModel('gemini-2.5-pro')








def generate_seirmodel_from_image(image_path: str, user_input: str, output_fileName: str) -> str:
    """
    Generates a SEIR model in XML format using a two-stage LLM process with multimodal input,
    and saves the full interaction log.

    Args:
        image_path (str): Path to the epidemiological model diagram image.
        user_input (str): Text containing tabular data (compartments, flows, variables).
        output_file_name (str): The desired name for the output XML file (e.g., "hiv_model.xml").

    Returns:
        str: A success message with the output file path, or an error message.
    """
    try:
        # Load the language specifications from a JSON file and convert to a pretty string
        with open(METAMODEL_FILENAME, "r", encoding="utf-8") as f:
            lang_specs_json = json.load(f)
        lang_specs = json.dumps(lang_specs_json, indent=2)
        
        # Load the image using the modern PIL library
        img_path = os.path.join(os.path.dirname(__file__), "diagrams", image_path)
        img = PIL.Image.open(img_path)

    except FileNotFoundError as err:
        print(f"Error: A required file was not found - {err}")
        return f"Error: A required file was not found - {err}"
    except Exception as err:
        print(f"An unexpected error occurred while reading files: {err}")
        return f"An unexpected error occurred while reading files: {err}"


    print(f"'{image_path}' loaded successfully.")
    print(f"'{METAMODEL_FILENAME}' loaded successfully.")
    # --- Construct the final prompt text ---
    separator = "\n" + "*" * 80 + "\n"


    llm1_input = (
        f"{separator}"
        f"PROMPT: \n{LLM1_PROMPT.strip()}\n"
        f"{separator}"
        f"METAMODEL: \n{lang_specs.strip()}\n"
        f"{separator}"
        f"USER_INPUT: \n{user_input.strip()}"
    )

    llm1 = model.generate_content([
        img,                 # The image object
        llm1_input.strip()  # The text part of the prompt
    ]).text.strip()


    llm2_input = (
        f"{separator}"
        f"PROMPT:\n{LLM2_PROMPT.strip()}\n"
        f"{separator}"
        f"USER INPUT:\n{user_input.strip()}\n"
        f"{separator}"
        f"STRUCTURALLY CORRECT SEIRMODEL FILE:\n{llm1.strip()}\n"
        f"{separator}"
    )

    # --- Call the modern API with a list of parts (image and text) ---
    llm2 = model.generate_content(llm2_input.strip()).text.strip()
    
    # --- Format and save the output ---
    output_content =(
        f"LLM1 PROMPT:\n{LLM1_PROMPT.strip()}"
        f"{separator}"
        f"METAMODEL:\n{lang_specs.strip()}"
        f"{separator}"
        f"User Input:\n{user_input.strip()}"
        f"{separator}"
        f"LLM1 RESPONSE:\n {llm1}"
        f"{separator}"
        f"{separator}"
        f"LLM2 PROMPT:\n{LLM2_PROMPT.strip()}"
        f"{separator}"
        f"USER INPUT AND LLM1'S RESPONSE (THE STRCTURALLY CORRECT SEIRMODEL) GOES HERE..."
        f"{separator}"
        f"LLM2'S RESPONSE:\n{llm2}"
    )

    try:
        # Ensure the output directory exists
        output_dir = os.path.join(os.path.dirname(output_fileName), "prompt_sample")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, os.path.basename(output_fileName))
        with open(output_file, "w", encoding="utf-8") as tf:
            tf.write(output_content)
    except IOError as e:
        return f"Error writing to output file '{output_fileName}': {e}"

    print(f"SEIR model successfully written to {output_fileName}")






# Constants for prompts and file names
EMPTY_PROMPT = "No Parameters provided, use the provided image to get the useful informations."

PROMPT_FOR_TEXT = """
You are now responsible for generating a complete SEIR model XML file using only the provided user input and XML language specification.
Do not assume any external context or missing information. Everything you need has already been provided.

You have access to:
- user_input: This includes all necessary compartment types, groups, and flows.
- language_specification: A skeleton XML that defines structure and format. Follow it exactly. Do not alter required lines.

Your output must be:
1. A valid and complete XML file in the format shown in the skeleton.
2. Use only the information given in user_input.
3. Output ONLY the XML file — no extra comments, notes, formatting, or text outside the XML.
4. If something is unclear, use a placeholder value with a comment like <!-- missing info -->.
5. The output will be parsed by a strict system. Maintain clean structure and formatting.
"""

PROMPT_WITH_IMAGE = """
You are now responsible for generating a complete SEIR model XML file using only the provided user input, image and language specification/metamodel of seirmodel.
Do not assume any external context or missing information. Everything you need has already been provided.

- model_diagram (image): This shows all compartments and directional flows.
- user_input (text): Provides parameter values, population numbers, and formulas.
- language_specification/metamodel (text): Make use of this file to understand the required XML structure and elements.

Instructions:
1. Extract compartments and transitions from the image (left to right, top-down if needed).
2. Use `user_input` to fill rates, formulas, and initial values.
3. Follow the XML structure exactly. No extra text or formatting.
4. Use 0-based indexing for compartments in order of appearance.
5. If any info is unclear, use `<!-- missing info -->` as placeholder.

Only return the final XML file.
"""


LLM1_PROMPT = """
You are an expert in XML structure generation for epidemiological models.

Your task is to generate a structurally correct SEIR model in XML format using the provided **model diagram (image)** and **language specification/metamodel**.

You must:
- Focus ONLY on generating compartment and flow structure.
- DO NOT attempt to calculate or insert any numeric rate values.
- Instead, use a placeholder `[[rate_missing]]` for all `rate` attributes that require computation later.
- Use 0-based indexing for compartments in the order they appear (top-down, left-to-right).
- Follow the metamodel strictly for element names, attributes, and nesting.
- Include all compartments and their directional flows shown in the diagram.

Inputs:
- model_diagram (image): Shows compartments and directional transitions.
- language_specification (text): Defines the structure and rules for valid SEIR XML.

Output:
- Only the final XML file. Do not include explanations or markdown formatting.
- Ensure all required attributes are present and validate against the provided metamodel.
"""

LLM2_PROMPT = """
You are an expert at interpreting epidemiological equations and inserting computed rates into XML model files.

You are given:
1. A partially completed SEIR XML file, where all rate fields are marked as [[rate_missing]].
2. A user_input section that includes all relevant parameter values, formulas, and **explicit population data (e.g., S, I, N)** if required for calculations.

YOUR TASK:
1. Identify each [[rate_missing]] inside an <outgoingFlows> tag.
2. Use the description and flow direction (source → target) to determine which rate formula applies.
3. Compute the rate using the correct formula and **ONLY THE VALUES EXPLICITLY PROVIDED in the user_input**.
   - For contact-based flows (e.g., βSI/N), use the **exact population values (S, I, N)** given in the user_input.
   - **CRITICAL: If any variable (like N, S, or I for contact rates) required for computation is NOT explicitly provided in the user_input, you MUST NOT assume a value or attempt to derive it. Instead, leave a clear comment stating the missing variable and why the rate cannot be computed.**
4. Before writing the rate, first add a detailed comment explaining your full reasoning.
5. Then insert the final computed value as the rate.

IMPORTANT RULES:
- Do not round — use full numerical precision at all times.
- **DO NOT modify the XML structure, tags, or ANY EXISTING ATTRIBUTES (e.g., 'target', 'description') in the provided XML file.** Your ONLY task is to calculate and insert the 'rate' value and add comprehensive comments.
- If a rate cannot be computed (due to missing data, as per Rule 3), leave a clear comment:
    ``

How to Write Reasoning (Baby-Step Style):
  For each <outgoingFlows> you process:
    First, add a full step-by-step comment above the rate:
      - Use simple language, no skipped math
      - Treat it like teaching someone new to equations
      - Explain each substitution and operation clearly
      - Then, insert the rate based on that computation.
  Example:

        <outgoingFlows rate="18" target="//@compartments.3" description="Example flow">
      </outgoingFlows>


Final Note: Your only task is to calculate and insert correct rate values. Please Do not add, remove, or reorder compartments or flows. Also don't change the target parameter in any ongoingrate tag.
"""


PROMPT_EXTRACT_PARAMETERS = """
You are an expert at extracting epidemiological model parameters from research data.
Given the diagram, user-provided data, and metadata, extract a table of all parameters.

Each parameter must include: 
- Source compartment
- Target compartment
- Equation (if applicable)
- Final value (if computable)
- Comments (provide you reasoning in detail, why did you come up with this value.)\n\n
- Respond ONLY with a description and a clear markdown table.
Note that your input will be used to generate a SEIR model, however my platform doesnt support contact based flow so you need to calculate then as rate based (used the inital population value rather than function).
Do not round any numerical values. Always show the full computed result with maximum precision.
"""


LANG_SPECS_FILENAME = "seirmodel_skeleton.txt"
METAMODEL_FILENAME = "metamodel.json"
METAMODEL_SKELETON_FILENAME = "metamodel_skeleton_seirmodel.txt"


#User Input
hiv_json = """
[{'compartment_index': 0,
  'PrimaryName': 'Recruitment',
  'SecondaryName': 'Homosexual Men',
  'outgoingFlows': [{'rate': '12.7872',
    'description': '𝛹𝜃(1−𝛾)',
    'target': '//@compartments.3'}]},
 {'compartment_index': 1,
  'PrimaryName': 'Recruitment',
  'SecondaryName': 'Women',
  'outgoingFlows': [{'rate': '173.16',
    'description': '𝛹(1−𝜃)',
    'target': '//@compartments.4'}]},
 {'compartment_index': 2,
  'PrimaryName': 'Recruitment',
  'SecondaryName': 'Heterosexual Men',
  'outgoingFlows': [{'rate': '147.0528',
    'description': '𝛹𝜃𝛾',
    'target': '//@compartments.5'}]},
 {'compartment_index': 3,
  'PrimaryName': 'Susceptible',
  'SecondaryName': 'Homosexual Men',
  'outgoingFlows': [{'rate': '0.09636',
    'description': 'λh',
    'target': '//@compartments.6'},
   {'rate': '0.0129', 'description': 'μ', 'target': '//@compartments.12'}]},
 {'compartment_index': 4,
  'PrimaryName': 'Susceptible',
  'SecondaryName': 'Women',
  'outgoingFlows': [{'rate': '1.637E-5',
    'description': 'λhw (From Homosexual Man) ',
    'target': '//@compartments.7'},
   {'rate': '1.355E-5',
    'description': 'λm (Form Woman)',
    'target': '//@compartments.7'},
   {'rate': '0.0129', 'description': 'μ ', 'target': '//@compartments.12'}]},
 {'compartment_index': 5,
  'PrimaryName': 'Susceptible',
  'SecondaryName': 'Heterosexual Men',
  'outgoingFlows': [{'rate': '2.5E-6',
    'description': 'λw (From Heterosexual Man)',
    'target': '//@compartments.8'},
   {'rate': '1.1368E-4',
    'description': 'λhm (From Homosexual Man)',
    'target': '//@compartments.8'},
   {'rate': '0.0129', 'description': 'μ', 'target': '//@compartments.12'}]},
 {'compartment_index': 6,
  'PrimaryName': 'Untreated Infected',
  'SecondaryName': 'Homosexual Men',
  'outgoingFlows': [{'rate': '0.0129',
    'description': 'μ',
    'target': '//@compartments.12'},
   {'rate': '0.29997', 'description': 'α * p', 'target': '//@compartments.9'},
   {'rate': '0.03333',
    'description': '1-p * α',
    'target': '//@compartments.10'}]},
 {'compartment_index': 7,
  'PrimaryName': 'Untreated Infected',
  'SecondaryName': 'Women',
  'outgoingFlows': [{'rate': '0.0129',
    'description': 'μ',
    'target': '//@compartments.12'},
   {'rate': '0.29997', 'description': 'p * α', 'target': '//@compartments.9'},
   {'rate': '0.03333',
    'description': 'α * 1-p',
    'target': '//@compartments.10'}]},
 {'compartment_index': 8,
  'PrimaryName': 'Untreated Infected',
  'SecondaryName': 'Heterosexual Men',
  'outgoingFlows': [{'rate': '0.0129',
    'description': 'μ',
    'target': '//@compartments.12'},
   {'rate': '0.29997', 'description': 'p * α', 'target': '//@compartments.9'},
   {'rate': '0.03333',
    'description': '1-p * α',
    'target': '//@compartments.10'}]},
 {'compartment_index': 9,
  'PrimaryName': 'Treated with ART',
  'SecondaryName': '',
  'outgoingFlows': [{'rate': '0.018',
    'description': 'δ',
    'target': '//@compartments.10'},
   {'rate': '0.0129', 'description': 'μ', 'target': '//@compartments.12'}]},
 {'compartment_index': 10,
  'PrimaryName': 'People living with AIDS',
  'SecondaryName': '',
  'outgoingFlows': [{'rate': '0.3333',
    'description': 'd',
    'target': '//@compartments.11'},
   {'rate': '0.0129', 'description': 'μ', 'target': '//@compartments.12'}]},
 {'compartment_index': 11,
  'PrimaryName': 'Death due to AIDS',
  'SecondaryName': '',
  'outgoingFlows': []},
 {'compartment_index': 12,
  'PrimaryName': 'Natural Death',
  'SecondaryName': '',
  'outgoingFlows': []}]
"""

hiv_all_info = """

Compartment Names with indexes:
0. Recruitment (Homosexual Men)
1. Recruitment (Women)
2. Recruitment (Heterosexual Men)
3. Susceptible (Homosexual Men)
4. Susceptible (Women)
5. Susceptible (Heterosexual Men)
6. Untreated Infected (Homosexual Men)
7. Untreated Infected (Women)
8. Untreated Infected (Heterosexual Men)
9. Treated with ART
10. People living with AIDS
11. Death due to AIDS
12. Natural Death


Flow direction and their parameters values:
Recruitment → Susceptible (Homosexual Men): 333 * 0.48 * (1 - 0.92) = 12.7872
Recruitment → Susceptible (Women): 333 * (1 - 0.48) = 173.16
Recruitment → Susceptible (Heterosexual Men): 333 * 0.48 * 0.92 = 147.0528

Susceptible (Homosexual Men) → Untreated Infected (Homosexual Men): λh = 0.44 * 7 * 79 / (2446 + 79) ≈ 0.09636
Susceptible (Homosexual Men) → Natural Death: μ = 0.0129

Susceptible (Women) → Untreated Infected (Women):  
- λhw (from homosexual men) = 0.018 * 2 * 79 / (2446 + 171173 + 79 + 29) ≈ 1.637E-5  
- λm (from women) = 0.02 * 4 * 6 / (189994 + 6) ≈ 1.355E-5  
Susceptible (Women) → Natural Death: μ = 0.0129

Susceptible (Heterosexual Men) → Untreated Infected (Heterosexual Men):  
- λw (from heterosexual men) = 0.02 * 4 * 29 / (171173 + 29) ≈ 2.5E-6  
- λhm (from homosexual men) = 0.25 * 1 * 79 / (2446 + 171173 + 79 + 29) ≈ 1.1368E-4  
Susceptible (Heterosexual Men) → Natural Death: μ = 0.0129

Untreated Infected → Treated with ART: α * p = 0.3333 * 0.9 = 0.29997  
Untreated Infected → People living with AIDS: α * (1 - p) = 0.3333 * 0.1 = 0.03333  
Untreated Infected → Natural Death: μ = 0.0129

Treated with ART → People living with AIDS: δ = 0.018  
Treated with ART → Natural Death: μ = 0.0129

People living with AIDS → Death due to AIDS: d = 0.3333  
People living with AIDS → Natural Death: μ = 0.0129
"""

hivModel = """
Table of Compartments
Index, Primary Name, Description
1, S_h(t), Susceptible homosexual men
2, I_h(t), Untreated infected homosexual men
3, S_w(t), Susceptible women
4, I_w(t), Untreated infected women
5, S_m(t), Susceptible heterosexual men
6, I_m(t), Untreated infected heterosexual men
7, T(t), Individuals treated with antiretrovirals
8, A(t), People living with AIDS

Table of Flows with Variables
From -> To, Description, Rate Expression / Parameter
∅ -> S_h, Recruitment of susceptible homosexual men, Ψθ(1-γ)
∅ -> S_w, Recruitment of susceptible women, Ψ(1-θ)
∅ -> S_m, Recruitment of susceptible heterosexual men, Ψθγ
S_h -> I_h, Infection of susceptible homosexual men, λ_h * S_h
S_w -> I_w, Infection of susceptible women, (λ_m + λ_hw) * S_w
S_m -> I_m, Infection of susceptible heterosexual men, (λ_w + λ_hm) * S_m
I_h, I_w, I_m -> T, Initial treatment of infected individuals, αp(I_h + I_w + I_m)
I_h, I_w, I_m -> A, Progression to AIDS for untreated individuals, α(1-p)(I_h + I_w + I_m)
T -> A, Progression to AIDS for treated individuals (e.g., treatment failure), δT
All -> death, Natural mortality, μ for each compartment
A -> death, AIDS-induced mortality, dA

Table of Parameters
Parameter, Meaning, Value (from paper)
Ψ, Recruitment rate into the susceptible population, 333 individuals/year
θ, Proportion of men in the population, 0.48
γ, Proportion of heterosexual men among all men, 0.92
p, Proportion of infected individuals who receive initial treatment, 0.90
μ, Natural mortality rate, 0.0129 per year
d, AIDS-induced mortality rate, 0.3333 per year
δ, Rate of AIDS development in treated individuals, 0.018 per year
α, Departure rate from infected compartments, 0.3333 per year
β_s, Probability of heterosexual transmission, 0.02
β_h, Probability of homosexual transmission, 0.44
β_hw, Probability of transmission from homosexual men to women, 0.018 (Assumed)
β_hm, Probability of transmission from homosexual men to heterosexual men, 0.25 (Assumed)
c_s, Rate of sexual partners for heterosexuals, 4 per year
c_h, Rate of sexual partners for homosexuals, 7 per year
c_hw, Rate of sexual partners between homosexual men and women, 2 per year
c_hm, Rate of sexual partners between homosexual and heterosexual men, 1 per year

"""

covidModel = """
Table of Compartments

Index: 1, Primary Name: Susceptible, Description: Individuals who can be infected
Index: 2, Primary Name: Exposed, Description: Individuals who have been exposed to the virus but are not yet infectious
Index: 3, Primary Name: Exposed (quarantined), Description: Exposed individuals identified via contact tracing and placed in quarantine
Index: 4, Primary Name: Infectious (presymptomatic), Description: Individuals who are infectious but have not yet developed symptoms
Index: 5, Primary Name: Infectious (presymptomatic, isolated), Description: Presymptomatic individuals who are in isolation
Index: 6, Primary Name: Infectious (mild to moderate), Description: Individuals with mild to moderate symptoms who are infectious
Index: 7, Primary Name: Infectious (mild to moderate, isolated), Description: Individuals with mild to moderate symptoms who are in isolation
Index: 8, Primary Name: Infectious (severe), Description: Individuals with severe symptoms requiring hospital admission
Index: 9, Primary Name: Infectious (severe, isolated), Description: Individuals with severe symptoms who are in isolation
Index: 10, Primary Name: Isolated, Description: A state for individuals with mild to moderate illness who are isolated and not hospitalized
Index: 11, Primary Name: Admitted to hospital (pre-ICU), Description: Individuals admitted to the hospital but not yet in the ICU
Index: 12, Primary Name: ICU, Description: Individuals admitted to the Intensive Care Unit
Index: 13, Primary Name: Admitted to hospital (post-ICU), Description: Individuals who have left the ICU but are still in the hospital
Index: 14, Primary Name: Recovered, Description: Individuals who have recovered and are assumed to be immune for the model's duration
Index: 15, Primary Name: Dead, Description: Individuals who have died from the infection; all deaths are assumed to occur in cases requiring intensive care
Table of Flows with Variables

From → To: Susceptible → Exposed, Description: Infection of a susceptible person, Governing Parameter / Rate: Governed by the basic reproduction number (R0) and contact patterns
From → To: Exposed → Infectious (presymptomatic), Description: End of latency period, becoming infectious, Governing Parameter / Rate: 1 / (Latent period)
From → To: Exposed → Exposed (quarantined), Description: Quarantine of exposed individuals, Governing Parameter / Rate: Percentage of exposed cases quarantined (varies by scenario)
From → To: Infectious (presymptomatic) → Infectious (mild to moderate OR severe), Description: End of presymptomatic period and onset of symptoms, Governing Parameter / Rate: 1 / (Presymptomatic infectious period)
From → To: Infectious → Isolated (various states), Description: Isolation of non-severe infectious cases due to testing, Governing Parameter / Rate: Percentage of non-quarantined cases tested and isolated (varies by age and scenario)
From → To: Infectious (mild to moderate) → Recovered, Description: Recovery from mild/moderate infection, Governing Parameter / Rate: 1 / (Infectious period for mild to moderate cases)
From → To: Infectious (severe) → Admitted to hospital (pre-ICU), Description: Hospital admission for severe cases, Governing Parameter / Rate: 1 / (Infectious period for severe cases)
From → To: Admitted to hospital (pre-ICU) → ICU, Description: Admission to ICU from a hospital bed, Governing Parameter / Rate: 1 / (Average length of stay in hospital before ICU)
From → To: Admitted to hospital (pre-ICU) → Recovered, Description: Recovery for hospitalized cases not requiring ICU, Governing Parameter / Rate: 1 / (Average length of stay in hospital for non-ICU cases)
From → To: ICU → Admitted to hospital (post-ICU), Description: Discharge from ICU to a hospital bed, Governing Parameter / Rate: 1 / (Average length of stay in ICU)
From → To: ICU → Dead, Description: Death in cases admitted to ICU, Governing Parameter / Rate: Probability of death in ICU cases (varies by age and comorbidity)
From → To: Admitted to hospital (post-ICU) → Recovered, Description: Recovery after ICU stay, Governing Parameter / Rate: 1 / (Average length of stay in hospital after ICU)
Table of Parameters

Parameter: Latent period, Meaning: Time from exposure to becoming infectious, Value (from paper): 2.5 days
Parameter: Presymptomatic infectious period, Meaning: Duration of infectiousness before symptom onset, Value (from paper): 1 day
Parameter: Infectious period (mild to moderate), Meaning: Duration of infectiousness for mild-to-moderate cases, Value (from paper): 6 days
Parameter: Infectious period (severe), Meaning: Time from symptom onset to hospital admission for severe cases, Value (from paper): 6 days
Parameter: Basic reproduction number (R0), Meaning: Average secondary infections from a primary case in a susceptible population, Value (from paper): 2.3
Parameter: Relative risk of transmission (isolated), Meaning: Reduction in transmission for isolated cases compared to non-isolated cases, Value (from paper): 0.1 (Assumption)
Parameter: Reduction in contacts, Meaning: Reduction in daily contacts due to physical distancing, Value (from paper): 60% (Physical distancing scenario) or 25% (Combination scenario)
Parameter: % Non-quarantined cases tested/isolated, Meaning: Percentage of infectious cases isolated (varies by age and scenario), Value (from paper): 10-80%
Parameter: % Exposed cases quarantined, Meaning: Percentage of exposed contacts who are quarantined, Value (from paper): 10% (Base case) or 30% (Enhanced detection/Combination scenarios)
Parameter: Probability of severe infection, Meaning: Chance of developing severe infection requiring hospitalization (varies by age/comorbidity), Value (from paper): 0.01 - 0.76
Parameter: Probability severe case requires ICU, Meaning: Chance a severe case is admitted to the ICU, Value (from paper): 0.26
Parameter: Probability of death in ICU, Meaning: Chance of death for an ICU patient (varies by age/comorbidity), Value (from paper): 0 - 1.0
Parameter: Length of stay (non-ICU), Meaning: Average hospital stay for cases not requiring ICU, Value (from paper): 10 days
Parameter: Length of stay (pre-ICU), Meaning: Average hospital stay before ICU admission, Value (from paper): 3 days
Parameter: Length of stay (in ICU), Meaning: Average duration of ICU stay, Value (from paper): 21 days
Parameter: Length of stay (post-ICU), Meaning: Average hospital stay after leaving the ICU, Value (from paper): 21 days

"""

simpleModel = """
| Index | Primary Name    | Description                           |
| ----- | --------------- | ------------------------------------- |
| 0     | Susceptible (S) | Individuals who can be infected       |
| 1     | Exposed (E)     | Infected but not yet infectious       |
| 2     | Infectious (I)  | Capable of transmitting the infection |
| 3     | Recovered (R)   | Immune but may lose immunity later    |


| From → To   | Description             | Rate Expression / Parameter |
| ----------- | ----------------------- | --------------------------- |
| S → E       | Infection               | **βSI/N**                   |
| E → I       | End of latency          | **σE**                      |
| I → R       | Recovery                | **γI**                      |
| R → S       | Loss of immunity        | **ωR**                      |
| All → death | Background mortality    | **µ** for each compartment  |
| I → null    | Infection-induced death | **αI**                      |
| ∅ → S       | Birth into Susceptible  | **µN**                      |


| Parameter | Meaning                                          | Value (from paper)                   |
| --------- | ------------------------------------------------ | ------------------------------------ |
| β         | Contact (transmission) rate                      | **0.21/day**                         |
| γ         | Recovery rate (1/γ is infectious period)         | **1/14 days** → γ ≈ **0.0714/day**   |
| σ         | Latency rate (1/σ is incubation period)          | **1/7 days** → σ ≈ **0.143/day**     |
| ω         | Immunity loss rate (1/ω is duration of immunity) | **1/365 days** → ω ≈ **0.00274/day** |
| µ         | Background birth/death rate                      | **1/76 years** → µ ≈ **3.6e-5/day**  |
| α         | Infection-induced mortality rate                 | **0** (assumed zero for this model)  |

"""


generate_seirmodel_from_image("hivModel(paper).jpeg", hivModel, "finalHivModel.txt")

time.sleep(10)

generate_seirmodel_from_image("covidModel(paper).png", covidModel, "finalCovidModel.txt")



#generate_seirmodel_from_image("simple_seirmodel.png", simpleModel, "finalSimpleModel.txt")