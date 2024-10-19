import os
import json
import git

# Get the repository root directory
git_repo = git.Repo(os.getcwd(), search_parent_directories=True)
git_root = git_repo.git.rev_parse("--show-toplevel")

column_config = {
    "omit": [
        "consent_*",
        "msoc_intro",
        "msoc_amenities_2",
        "msoc_ladder"
    ],
    "non_standard_exploding": {
        "msoc_live_table": ["msoc_live_country0", "msoc_live_country11", "msoc_live_country25", "msoc_live_country35", "msoc_live_country46", "msoc_live_country66", "msoc_live_countryrec", "msoc_live_state0", "msoc_live_state11", "msoc_live_state25", "msoc_live_state35", "msoc_live_state46", "msoc_live_state66", "msoc_live_staterec", "msoc_live_city0", "msoc_live_city11", "msoc_live_city25", "msoc_live_city35", "msoc_live_city46", "msoc_live_city66", "msoc_live_cityrec"],
        "msoc_lang1rev": ["msoc_21rev", "msoc_21arev", "msoc_21brev", "msoc_21crev", "msoc_21drev", "msoc_21erev", "msoc_22rev", "msoc_22arev", "msoc_22brev", "msoc_22crev", "msoc_22drev", "msoc_22erev", "msoc_23rev", "msoc_23arev", "msoc_23brev", "msoc_23crev", "msoc_23drev", "msoc_23erev", "msoc_24rev", "msoc_24arev", "msoc_24brev", "msoc_24crev", "msoc_24drev", "msoc_24erev"],
        "msoc_lang2rev": ["msoc_21frev", "msoc_21grev", "msoc_21hrev", "msoc_21irev", "msoc_22frev", "msoc_22grev", "msoc_22hrev", "msoc_22irev", "msoc_23frev", "msoc_23grev", "msoc_23hrev", "msoc_23irev", "msoc_24frev", "msoc_24grev", "msoc_24hrev", "msoc_24irev"],
        "msoc_lang3rev": ["msoc_21jrev", "msoc_21krev", "msoc_21lrev", "msoc_21mrev", "msoc_21nrev", "msoc_21orev", "msoc_22jrev", "msoc_22krev", "msoc_22lrev", "msoc_22mrev", "msoc_22nrev", "msoc_22orev", "msoc_23jrev", "msoc_23krev", "msoc_23lrev", "msoc_23mrev", "msoc_23nrev", "msoc_23orev", "msoc_24jrev", "msoc_24krev", "msoc_24lrev", "msoc_24mrev", "msoc_24nrev", "msoc_24orev"],
        "msoc_lang4rev": ["msoc_21prev", "msoc_21qrev", "msoc_21rrev", "msoc_21srev", "msoc_22prev", "msoc_22qrev", "msoc_22rrev", "msoc_22srev", "msoc_23prev", "msoc_23qrev", "msoc_23rrev", "msoc_23srev", "msoc_24prev", "msoc_24qrev", "msoc_24rrev", "msoc_24srev"],
        "msoc_household": ["msoc_household_0", "msoc_household_1", "msoc_household_2", "msoc_household_3", "msoc_household_4", "msoc_household_5", "msoc_household_6", "msoc_household_7", "msoc_household_8", "msoc_household_9", "msoc_household_10", "msoc_household_11", "msoc_household_12", "msoc_household_13"],
        "msoc_amenities": ["msoc_elec_0", "msoc_elec_11", "msoc_elec_25", "msoc_elec_35", "msoc_elec_46", "msoc_elec_66", "msoc_elec_rec", "msoc_rad_0", "msoc_rad_11", "msoc_rad_25", "msoc_rad_35", "msoc_rad_46", "msoc_rad_66", "msoc_rad_rec", "msoc_tv_0", "msoc_tv_11", "msoc_tv_25", "msoc_tv_35", "msoc_tv_46", "msoc_tv_66", "msoc_tv_rec", "msoc_ref_0", "msoc_ref_11", "msoc_ref_25", "msoc_ref_35", "msoc_ref_46", "msoc_ref_66", "msoc_ref_rec", "msoc_wash_0", "msoc_wash_11", "msoc_wash_25", "msoc_wash_35", "msoc_wash_46", "msoc_wash_66", "msoc_wash_rec", "msoc_comp_0", "msoc_comp_11", "msoc_comp_25", "msoc_comp_35", "msoc_comp_46", "msoc_comp_66", "msoc_comp_rec", "msoc_line_0", "msoc_line_11", "msoc_line_25", "msoc_line_35", "msoc_line_46", "msoc_line_66", "msoc_line_rec", "msoc_runn_0", "msoc_runn_11", "msoc_runn_25", "msoc_runn_35", "msoc_runn_46", "msoc_runn_66", "msoc_runn_rec", "msoc_wat_0", "msoc_wat_11", "msoc_wat_25", "msoc_wat_35", "msoc_wat_46", "msoc_wat_66", "msoc_wat_rec", "msoc_bath_0", "msoc_bath_11", "msoc_bath_25", "msoc_bath_35", "msoc_bath_46", "msoc_bath_66", "msoc_bath_rec", "msoc_car_0", "msoc_car_11", "msoc_car_25", "msoc_car_35", "msoc_car_46", "msoc_car_66", "msoc_car_rec", "msoc_inter_0", "msoc_inter_11", "msoc_inter_25", "msoc_inter_35", "msoc_inter_46", "msoc_inter_66", "msoc_inter_rec", "msoc_sound_0", "msoc_sound_11", "msoc_sound_25", "msoc_sound_35", "msoc_sound_46", "msoc_sound_66", "msoc_sound_rec", "msoc_smrt_0", "msoc_smrt_11", "msoc_smrt_25", "msoc_smrt_35", "msoc_smrt_46", "msoc_smrt_66", "msoc_smrt_rec", "msoc_bedr_0", "msoc_bedr_11", "msoc_bedr_25", "msoc_bedr_35", "msoc_bedr_46", "msoc_bedr_66", "msoc_bedr_rec"],
        "msoc_obj_num": ["msoc_ob1_0", "msoc_ob1_11", "msoc_ob1_25", "msoc_ob1_35", "msoc_ob1_46", "msoc_ob1_66", "msoc_ob1_rec", "msoc_ob2_0", "msoc_ob2_11", "msoc_ob2_25", "msoc_ob2_35", "msoc_ob2_46", "msoc_ob2_66", "msoc_ob2_rec", "msoc_ob3_0", "msoc_ob3_11", "msoc_ob3_25", "msoc_ob3_35", "msoc_ob3_46", "msoc_ob3_66", "msoc_ob3_rec", "msoc_ob4_0", "msoc_ob4_11", "msoc_ob4_25", "msoc_ob4_35", "msoc_ob4_46", "msoc_ob4_66", "msoc_ob4_rec", "msoc_ob5_0", "msoc_ob5_11", "msoc_ob5_25", "msoc_ob5_35", "msoc_ob5_46", "msoc_ob5_66", "msoc_ob5_rec"],
        "msoc_bas_1": ["msoc_bas_0", "msoc_bas_11", "msoc_bas_25", "msoc_bas_35", "msoc_bas_46", "msoc_bas_66", "msoc_bas_rec"],
        "msoc_fin_1": ["msoc_fin_0", "msoc_fin_11", "msoc_fin_25", "msoc_fin_35", "msoc_fin_46", "msoc_fin_66", "msoc_fin_rec"],
        "msoc_care_1": ["msoc_care_0", "msoc_care_11", "msoc_care_25", "msoc_care_35", "msoc_care_46", "msoc_care_66", "msoc_care_rec"],
        "msoc_eat_1": ["msoc_eat_0", "msoc_eat_11", "msoc_eat_25", "msoc_eat_35", "msoc_eat_46", "msoc_eat_66", "msoc_eat_rec"],
        "msoc_bal_1": ["msoc_bal_0", "msoc_bal_11", "msoc_bal_25", "msoc_bal_35", "msoc_bal_46", "msoc_bal_66", "msoc_bal_rec"],
        "msoc_ladder": ["msoc_ladder_0", "msoc_ladder_11", "msoc_ladder_25", "msoc_ladder_35", "msoc_ladder_46", "msoc_ladder_66", "msoc_ladder_rec"]
    }
}

column_config_file = os.path.join(git_root, 'reference', 'column_config.json')
with open(column_config_file, 'w', encoding='utf-8') as f:
    json.dump(column_config, f, indent=2, ensure_ascii=False)

print(f"Column configuration saved to {column_config_file}")
