from collections import OrderedDict

from wazimap.geo import geo_data
from wazimap.data.tables import get_model_from_fields
from wazimap.data.utils import get_session, calculate_median, merge_dicts, get_stat_data, get_objects_by_geo, group_remainder
import logging

# ensure tables are loaded
import janaganana.tables  # noqa

PROFILE_SECTIONS = (
    'demographics',
    'religion',
    'age',
    'education',
    'maritalstatus',
    'workers'
)

# Education recodes
EDUCATION_LEVEL_PASSED_RECODES = OrderedDict([
    ('PRIMARY_1_5', 'Primary'),
    ('LOWER_SECONDARY_6_8', 'Lower Secondary'),
    ('SECONDARY_9_10', 'Secondary'),
    ('SLC_AND_EQUIVALENT', 'SLC'),
    ('INTERMEDIATE', 'Intermed.'),
    ('BEGINNER', 'Beginner'),
    ('NON_FORMAL', 'Non-formal'),
    ('GRADUATE', 'Graduate'),
    ('POST_GRADUATE_AND_ABOVE', 'Post-graduate and Above'),
    ('NOT_STATED', 'Not Stated'),
    ('OTHERS', 'Others')
])


def sort_stats_result(ip,key=None):
    metadata = ip['metadata']
    del ip['metadata']
    rv = None
    if key:
        sorted_od = sorted(ip.values(), key=lambda x: x[key]['numerators']['this'], reverse=True)
        rv = OrderedDict([(i['metadata']['name'], i) for i in sorted_od])
    else:
        sorted_od = sorted(ip.values(), key=lambda x: x['numerators']['this'], reverse=True)
        rv = OrderedDict([(i['name'], i) for i in sorted_od])
    rv['metadata'] = metadata
    return rv


def get_census_profile(geo_code, geo_level, profile_name=None):
    session = get_session()

    try:
        geo_summary_levels = geo_data.get_summary_geo_info(geo_code, geo_level)
        data = {}

        for section in PROFILE_SECTIONS:
            function_name = 'get_%s_profile' % section
            if function_name in globals():
                func = globals()[function_name]
                data[section] = func(geo_code, geo_level, session)

                # get profiles for province and/or country
                for level, code in geo_summary_levels:
                    # merge summary profile into current geo profile
                    merge_dicts(data[section], func(code, level, session), level)
        return data

    finally:
        session.close()


SEX_RECODES = OrderedDict([
    ('FEMALE', 'Female'),
    ('MALE', 'Male')
])

AREA_RECODES = OrderedDict([
    ('RURAL', 'Rural'),
    ('URBAN', 'Urban')
])


LITERACY_RECODES = OrderedDict([
    ('LITERATE', 'Literate'),
    ('ILLITERATE', 'Illiterate')
])

RELIGION_RECODES = OrderedDict([
    ('HINDU', 'Hindu'),
    ('MUSLIM', 'Muslim'),
    ('CHRISTIAN', 'Christian'),
    ('SIKH', 'Sikh'),
    ('JAIN', 'Jain'),
    ('BUDDHIST', 'Buddhist'),
    ('OTHERS', 'Other')
])

def get_demographics_profile(geo_code, geo_level, session):

    population_by_area_dist_data, total_population_by_area = get_stat_data(
        'area', geo_level, geo_code, session,
        recode=dict(AREA_RECODES),
        key_order=AREA_RECODES.values(),
        table_fields=['area', 'sex'])

    population_by_area_dist_data = sort_stats_result(population_by_area_dist_data)

    population_by_sex_dist_data, _ = get_stat_data(
        'sex', geo_level, geo_code, session,
        recode=dict(SEX_RECODES),
        key_order=SEX_RECODES.values(),
        table_fields=['area', 'sex'])

    population_by_sex_dist_data = sort_stats_result(population_by_sex_dist_data)

    literacy_dist_data, _ = get_stat_data(
        'literacy', geo_level, geo_code, session,
        recode=dict(LITERACY_RECODES),
        key_order=LITERACY_RECODES.values(),
        table_fields=['area', 'literacy', 'sex'])

    literacy_dist_data = sort_stats_result(literacy_dist_data)

    literacy_by_sex, t_lit = get_stat_data(
        ['sex', 'literacy'], geo_level, geo_code, session,
        table_fields=['area', 'literacy', 'sex'],
        recode={'literacy': dict(LITERACY_RECODES)},
        key_order={'literacy': LITERACY_RECODES.values()},
        percent_grouping=['sex'])

    literacy_by_area, t_lit = get_stat_data(
        ['area', 'literacy'], geo_level, geo_code, session,
        table_fields=['area', 'literacy', 'sex'],
        recode={'area': dict(AREA_RECODES)},
        key_order={'area': AREA_RECODES.values()},
        percent_grouping=['area'])

    final_data = {
        # 'sex_ratio': sex_dist_data,
        'population_area_ratio': population_by_area_dist_data,
        'population_sex_ratio': population_by_sex_dist_data,
        'literacy_by_sex_distribution': literacy_by_sex,
        'literacy_ratio': literacy_dist_data,
        'literacy_by_area_distribution': literacy_by_area,
        'disability_ratio': 123,
        'total_population': {
            "name": "People",
            "values": {"this": total_population_by_area}
        },
        'total_disabled': {
            'name': 'People',
            'values':
                {'this': 111},
        }
    }

    return final_data

def get_religion_profile(geo_code, geo_level, session):

    religion_dist_data, _ = get_stat_data(
        'religion', geo_level, geo_code, session,
        # recode=dict(RELIGION_RECODES),
        # key_order=RELIGION_RECODES.values(),
        table_fields=['area', 'religion', 'sex'])

    religion_dist_data = sort_stats_result(religion_dist_data)

    religion_by_sex, t_lit = get_stat_data(
        ['religion', 'sex'], geo_level, geo_code, session,
        table_fields=['area', 'religion', 'sex'],
        # recode={'religion': dict(RELIGION_RECODES)},
        # key_order={'religion': RELIGION_RECODES.values()},
        key_order={'sex': SEX_RECODES.values()},
        percent_grouping=['sex'])

    religion_by_sex = sort_stats_result(religion_by_sex, 'Female')

    religion_by_area, t_lit = get_stat_data(
        ['religion', 'area'], geo_level, geo_code, session,
        table_fields=['area', 'religion', 'sex'],
        recode={'area': dict(AREA_RECODES)},
        key_order={'area': AREA_RECODES.values()},
        percent_grouping=['area'])

    religion_by_area = sort_stats_result(religion_by_area, 'Urban')

    total_population_by_area=10000000000

    final_data = {
        'religion_ratio': religion_dist_data,
        'religion_by_area_distribution': religion_by_area,
        'religion_by_sex_distribution':religion_by_sex,
        'disability_ratio': 123,
        'total_population': {
            "name": "People",
            "values": {"this": t_lit}
        }
    }

    return final_data

def get_age_profile(geo_code, geo_level, session):

    # age category
    def age_cat_recode(f, x):

        if x.endswith('+'):
            age = 80
        elif x == 'Age not stated':
            age = 65
        else:
            age = int(x.split('-')[0])

        if age < 18:
            return 'Under 18'
        elif age >= 65:
            return '65 and over'
        elif age >= 40:
            return '40 and 65'
        else:
            return '18 to 40'

    # age in 10 year groups
    def age_recode(f, x):

        if f in ('sex', 'area'):
            return x

        if x.endswith('+'):
            age = int(x.replace('+', ''))
        elif x == 'Age not stated':
            return x
        else:
            age = int(x.split('-')[0])

        if age >= 80:
            return '80+'
        bucket = 10 * (age / 10)
        return '%d-%d' % (bucket, bucket + 9)

    age_dist_data, _ = get_stat_data(
        'age', geo_level, geo_code, session,
        table_fields=['area', 'age', 'sex'],
        recode=age_cat_recode)

    age_dist_data = sort_stats_result(age_dist_data)


    age_by_sex, t_lit = get_stat_data(
        ['age', 'sex'], geo_level, geo_code, session,
        table_fields=['area', 'age', 'sex'],
        recode=age_recode,
        key_order={'sex': SEX_RECODES.values()},
        percent_grouping=['sex'])

    age_by_area, t_lit = get_stat_data(
        ['age', 'area'], geo_level, geo_code, session,
        table_fields=['area', 'age', 'sex'],
        recode=age_recode,
        key_order={'area': AREA_RECODES.values()},
        percent_grouping=['area'])

    final_data = {
        'age_ratio': age_dist_data,
        'age_by_area_distribution': age_by_area,
        'age_by_sex_distribution': age_by_sex,
        'disability_ratio': 123,
        'total_population': {
            "name": "People",
            "values": {"this": t_lit}
        }
    }

    return final_data

def get_education_profile(geo_code, geo_level, session):

    education_dist_data, _ = get_stat_data(
        'education', geo_level, geo_code, session,
        # recode=dict(education_RECODES),
        # key_order=education_RECODES.values(),
        table_fields=['area', 'education', 'sex'])

    education_dist_data = sort_stats_result(education_dist_data)

    education_by_sex, t_lit = get_stat_data(
        ['education', 'sex'], geo_level, geo_code, session,
        table_fields=['area', 'education', 'sex'],
        # recode={'education': dict(education_RECODES)},
        # key_order={'education': education_RECODES.values()},
        key_order={'sex': SEX_RECODES.values()},
        percent_grouping=['sex'])

    education_by_sex = sort_stats_result(education_by_sex, 'Female')

    education_by_area, t_lit = get_stat_data(
        ['education', 'area'], geo_level, geo_code, session,
        table_fields=['area', 'education', 'sex'],
        recode={'area': dict(AREA_RECODES)},
        key_order={'area': AREA_RECODES.values()},
        percent_grouping=['area'])

    education_by_area = sort_stats_result(education_by_area, 'Urban')

    final_data = {
        'education_ratio': education_dist_data,
        'education_by_area_distribution': education_by_area,
        'education_by_sex_distribution':education_by_sex,
        'disability_ratio': 123,
        'total_population': {
            "name": "People",
            "values": {"this": t_lit}
        }
    }

    return final_data

def get_maritalstatus_profile(geo_code, geo_level, session):
    maritalstatus_dist_data, _ = get_stat_data(
        'maritalstatus', geo_level, geo_code, session,
        # recode=dict(education_RECODES),
        # key_order=education_RECODES.values(),
        table_fields=['area', 'maritalstatus', 'sex'])

    maritalstatus_dist_data = sort_stats_result(maritalstatus_dist_data)

    maritalstatus_by_sex, t_lit = get_stat_data(
        ['maritalstatus', 'sex'], geo_level, geo_code, session,
        table_fields=['area', 'maritalstatus', 'sex'],
        recode={'sex': dict(SEX_RECODES)},
        key_order={'sex': SEX_RECODES.values()},
        percent_grouping=['sex'])

    maritalstatus_by_sex = sort_stats_result(maritalstatus_by_sex, 'Female')

    maritalstatus_by_area, t_lit = get_stat_data(
        ['maritalstatus', 'area'], geo_level, geo_code, session,
        table_fields=['area', 'maritalstatus', 'sex'],
        recode={'area': dict(AREA_RECODES)},
        key_order={'area': AREA_RECODES.values()},
        percent_grouping=['area'])

    maritalstatus_by_area = sort_stats_result(maritalstatus_by_area, 'Urban')

    final_data = {
        'maritalstatus_ratio': maritalstatus_dist_data,
        'maritalstatus_by_area_distribution': maritalstatus_by_area,
        'maritalstatus_by_sex_distribution': maritalstatus_by_sex,
        'disability_ratio': 123,
        'total_population': {
            "name": "People",
            "values": {"this": t_lit}
        }
    }

    return final_data


def get_workers_profile(geo_code, geo_level, session):

    workers_dist_data, _ = get_stat_data(
        'workers', geo_level, geo_code, session,
        table_fields=['area', 'workers', 'workerssex'])

    workers_dist_data = sort_stats_result(workers_dist_data)

    workers_by_sex, t_lit = get_stat_data(
        ['workers', 'workerssex'], geo_level, geo_code, session,
        table_fields=['area', 'workers', 'workerssex'],
        key_order={'workerssex': SEX_RECODES.values()},
        percent_grouping=['workerssex'])

    workers_by_sex = sort_stats_result(workers_by_sex, 'Female')

    workers_by_area, t_lit = get_stat_data(
        ['workers', 'area'], geo_level, geo_code, session,
        table_fields=['area', 'workers', 'workerssex'],
        recode={'area': dict(AREA_RECODES)},
        key_order={'area': AREA_RECODES.values()},
        percent_grouping=['area'])

    workers_by_area = sort_stats_result(workers_by_area, 'Urban')

    final_data = {
        'workers_ratio': workers_dist_data,
        'workers_by_area_distribution': workers_by_area,
        'workers_by_sex_distribution':workers_by_sex,
        'disability_ratio': 123,
        'total_population': {
            "name": "People",
            "values": {"this": t_lit}
        }
    }

    return final_data
