import argparse
import os
from utils import get_patient_init_date
from pre_cohort import exclude
from pre_cohort_rx import pre_user_cohort_rx_v2
from pre_cohort_dx import get_user_cohort_dx
from pre_demo import get_user_cohort_demo
from pre_outcome import pre_user_cohort_outcome
from user_cohort import pre_user_cohort_triplet
import pickle


def parse_args():
    parser = argparse.ArgumentParser(description='process parameters')
    # parser.add_argument('--min_patients', default=500, type=int,help='minimum number of patients for each cohort.')
    parser.add_argument('--min_patients', default=2, type=int,help='minimum number of patients for each cohort.')
    parser.add_argument('--min_prescription', default=2, type=int,help='minimum times of prescriptions of each drug.')
    parser.add_argument('--time_interval', default=30, type=int,help='minimum time interval for every two prescriptions')
    parser.add_argument('--followup', default=730, type=int, help='number of days of followup period')
    parser.add_argument('--baseline', default=365, type=int, help='number of days of baseline period')
    # parser.add_argument('--input_data', default='../data/CAD')
    parser.add_argument('--input_data', default='../data/synthetic')
    parser.add_argument('--pickles', default='pickles')
    parser.add_argument('--outcome_icd9', default='outcome_icd9.txt', help='outcome definition with ICD-9 codes')
    parser.add_argument('--outcome_icd10', default='outcome_icd10.txt', help='outcome definition with ICD-10 codes')
    parser.add_argument('--save_cohort_all', default='save_cohort_all/')

    args = parser.parse_args()
    return args


def get_patient_list(min_patient, cad_prescription_taken_by_patient):
    patients_list = set()
    for drug, patients in cad_prescription_taken_by_patient.items():
        if len(patients) >= min_patient:
            for patient in patients:
                patients_list.add(patient)
    return patients_list


def main(args):

    print('Loading prescription data...')

    # pickle is generated from input table drug.csv (pre_drug.py)
    # default_dict of drugs of format {drug_id: {patient_id:{(date, num_of_days), (date, num_of_days)}}}
    cad_prescription_taken_by_patient = pickle.load(
        open(os.path.join(args.pickles, 'cad_prescription_taken_by_patient.pkl'), 'rb'))

    # taken from Cohort.csv
    # patient_1stDX_date - first diagnosis encounter {patient_id: datetime} (index_date field in cohort.csv),
    # patient_start_date - date of insurance enrollment start {patient_id: datetime} (DTSTART field in cohort.csv)
    patient_1stDX_date, patient_start_date = get_patient_init_date(args.input_data, args.pickles)

    # icd9, icd10 code to ccs (clinical classification software) - typo in variable names (css)
    # https://www.hcup-us.ahrq.gov/toolssoftware/ccs/AppendixASingleDX.txt
    icd9_to_css = pickle.load(open(os.path.join(args.pickles, 'icd9_to_css.pkl'), 'rb'))
    icd10_to_css = pickle.load(open(os.path.join(args.pickles, 'icd10_to_css.pkl'), 'rb'))

    print('Preprocessing patient data...')

    # drugs and patients to preserve for study
    # 1. exclude patients whose index date (first day of prescription of any drug) prior to 1st DX
    # 2. exclude patients who fail to constantly take the drug within 730 days (interval <= 90)
    # 3. exclude patients whose baseline period (time before index date) is less than 365 days
    # save_prescription[drug][patient] = dates; save_patient[patient][drug] = dates;
    save_prescription, save_patient = exclude(cad_prescription_taken_by_patient, patient_1stDX_date,
                                                   patient_start_date, args.time_interval,
                                                   args.followup, args.baseline)

    # if for any drug a number of users >= args.min_patients all those patients are added to a combined set of patients
    patient_list = get_patient_list(args.min_patients, save_prescription)

    # for each DRUG get patient_ids with any of theirs prescriptions that happened before that DRUG has been prescribed
    # basically all those drugs, for which we plan to emulate RCT
    # save_cohort_rx[drug][patient_id][date][drug_id_1, drug_id_2]
    save_cohort_rx = pre_user_cohort_rx_v2(save_prescription, save_patient, args.min_patients)

    # for each DRUG get patient_ids with all of theirs diagnosis (ccs), diagnosed before that DRUG has been prescribed
    # save_cohort_dx[drug][patient_id][date][ccs_code_1, ccs_code_2]
    save_cohort_dx = get_user_cohort_dx(args.input_data, save_prescription, icd9_to_css, icd10_to_css, args.min_patients, patient_list)

    # get cohort demographic info (date of birth, gender)
    save_cohort_demo = get_user_cohort_demo(args.input_data, patient_list)

    save_cohort_outcome = {}
    # Heart Failure
    codes9 = ['425', '428', '40201', '40211', '40291', '40401', '40403', '40411', '40413', '40491', '40493', 'K77']
    codes0 = ['I11', 'I13', 'I50', 'I42', 'K77']
    # heart failure patients:
    # save_cohort_outcome{heart-failure:{patient_id:[dates of heart_failure dx], patient_id...}
    save_cohort_outcome['heart-failure'] = pre_user_cohort_outcome(args.input_data, patient_list, codes9, codes0)

    # Stroke
    codes9 = ['4380', '4381', '4382', '4383', '4384', '4385', '4386', '4387', '4388', '4389', 'V1254']
    codes0 = ['Z8673', 'I60', 'I61', 'I62', 'I63', 'I64', 'I65', 'I66', 'I67', 'I68', 'I69', 'G458', 'G459']
    # stroke patients
    save_cohort_outcome['stroke'] = pre_user_cohort_outcome(args.input_data,patient_list, codes9, codes0)

    print('Generating patient cohort...')
    pre_user_cohort_triplet(save_prescription, save_cohort_rx, save_cohort_dx,
                            save_cohort_outcome, save_cohort_demo, args.save_cohort_all)


if __name__ == '__main__':
    main(args=parse_args())
