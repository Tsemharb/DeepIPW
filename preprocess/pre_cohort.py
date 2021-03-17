from collections import defaultdict
from datetime import datetime


# 1. exclude patients whose index date prior to 1st DX
# 2. exclude patients who fail to constantly take the drug within 730 days (interval <= 90)
# 3. exclude patients whose baseline period (time before index date) is less than 365 days


def exclude(cad_prescription_taken_by_patient, patient_1stDX_date, patient_start_date, interval,
            followup, baseline):
    cad_prescription_taken_by_patient_exclude = defaultdict(dict)
    cad_patient_take_prescription_exclude = defaultdict(dict)

    for drug, taken_by_patient in cad_prescription_taken_by_patient.items():
        for patient, take_times in taken_by_patient.items():
            dates = [datetime.strptime(date, '%m/%d/%Y') for (date, days) in take_times if date and days]
            dates = sorted(dates)
            dates_days = {datetime.strptime(date, '%m/%d/%Y'): int(days) for (date, days) in take_times if
                          date and days}
            DX = patient_1stDX_date.get(patient, datetime.max)  # diagnosis date
            index_date = dates[0]  # first day of prescription
            start_date = patient_start_date.get(patient, datetime.max)  # enrollment start day
            # if criteria_1_is_valid(index_date, DX) \
            #         and criteria_2_is_valid(dates, interval, followup, dates_days) \
            #         and criteria_3_is_valid(index_date, start_date, baseline):
            if True:
                cad_prescription_taken_by_patient_exclude[drug][patient] = dates
                cad_patient_take_prescription_exclude[patient][drug] = dates

    return cad_prescription_taken_by_patient_exclude, cad_patient_take_prescription_exclude


# drug is taken after the DX (target_cohort diagnosis)
def criteria_1_is_valid(index_date, DX):
    return (index_date - DX).days > 0


# 730 days of continuous treatment. Time between drug precriptions < interval
def criteria_2_is_valid(dates, interval, followup, dates_days):
    if (dates[-1] - dates[0]).days <= (followup - 89):
        return False
    for i in range(1, len(dates)):
        sup_day = dates_days.get(dates[i - 1])
        if (dates[i] - dates[i - 1]).days - sup_day > interval:
            return False

    return True


# first drug prescription at least baseline (365 days) after start_date (enrollment start day)
def criteria_3_is_valid(index_date, start_date, baseline):
    return (index_date - start_date).days >= baseline
