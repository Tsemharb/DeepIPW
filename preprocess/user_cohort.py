from datetime import  datetime
import pickle
from tqdm import tqdm


def pre_user_cohort_triplet(cad_prescription_taken_by_patient, cad_user_cohort_rx, cad_user_cohort_dx,
                            save_cohort_outcome,
                    cad_user_cohort_demo, out_file_root):
    cohorts_size = dict()
    # for each drug saved for RCT
    for drug, taken_by_patient in tqdm(cad_user_cohort_rx.items()):
        file_x = '{}/{}.pkl'.format(out_file_root, drug)
        triples = []
        # for each patient for that drug
        for patient, taken_times in taken_by_patient.items():
            # get earliest date of the drug intake
            index_date = cad_prescription_taken_by_patient.get(drug).get(patient)[0]
            # get this patient's diagnoses
            try:
                dx = cad_user_cohort_dx.get(drug).get(patient)
            except:
                pass
            # get this patient's demographics data (year of birth, gender(1-male, 2-female)
            demo = cad_user_cohort_demo.get(patient)
            # get demographic date in form(age at the start of taking a drug, gender(0-male, 1-female)
            demo_feature_vector =get_demo_feature_vector(demo, index_date)

            outcome_feature_vector = []
            # for each outcome of interest (heart-failure, stroke)
            for outcome_name, outcome_map in save_cohort_outcome.items():
                # get the dates of outcome diagnoses (stroke, heart failure)
                outcome_dates = outcome_map.get(patient, [])
                dates = [datetime.strptime(date.strip('\n'), '%m/%d/%Y') for date in outcome_dates if date]
                dates = sorted(dates)
                # if drug is taken no more than in two years window before outcome diagnosis (stroke, heart failure)
                outcome_feature_vector.append(get_outcome_feature_vector(dates, index_date))

            # 1 if patient has the outcome or 0 otherwise
            outcome = max(outcome_feature_vector)

            rx_codes, dx_codes = [], []

            if taken_times:
                rx_codes = [rx_code for date, rx_code in sorted(taken_times.items(), key= lambda x:x[0])]
            # get patient's diagnoses
            if dx:
                dx_codes = [list(dx_code) for date, dx_code in sorted(dx.items(), key= lambda x:x[0])]

            # patient_id, [patient's drugs, patient's diagnoses, age, gender], outcome(0 or 1)
            triple = (patient, [rx_codes, dx_codes, demo_feature_vector[0], demo_feature_vector[1]],outcome)
            triples.append(triple)

        cohorts_size['{}.pkl'.format(drug)] = len(triples)
        pickle.dump(triples, open(file_x, 'wb'))

    pickle.dump(cohorts_size, open('{}/cohorts_size.pkl'.format(out_file_root), 'wb'))


def get_outcome_feature_vector(dates, index_date):
    for date in dates:
        if date > index_date and (date - index_date).days <= 730:
            return 1
    return 0


def get_demo_feature_vector(demo, index_date):
    if not demo:
        return [0, 0]
    db, sex = demo
    index_date_y = index_date.year
    age = index_date_y - int(db)
    sex_n = int(sex) - 1
    return [age, sex_n]
