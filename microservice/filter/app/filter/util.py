import re
import math
import json

from app.logging import logger
from fuzzywuzzy import fuzz

def parse_experiance_years(exp_str):
    exp_str = exp_str.lower()
    date_strings = ["year", "month","week","day"]
    day_map = [365, 30, 7 , 1]

    final_days = 0

    # logger.info("starting for %s" , exp_str)
    has_plus = False
    has_dash = False

    for dateIdx, date_str in enumerate(date_strings):
        if date_str in exp_str or date_str+"s" in exp_str:
            # found a match
            if date_str+"s" in exp_str:
                matchStr = date_str+"s"
            elif date_str in exp_str:
                matchStr = date_str

            logger.debug("match string found is %s", matchStr)

            # is match string a complete word or not like there can be mistakes like 6months without a space also case can be like 6months.
            if matchStr not in exp_str.split(" "):
                logger.debug("match string is not a word")
                exp_str = exp_str.replace(matchStr, " " + matchStr + " ")
                exp_str = re.sub(' +', ' ', exp_str)

            words = exp_str.split(" ")

            logger.debug("words %s", words)

            index = words.index(matchStr)

            logger.debug("match string index is %s" , index)

            # expect the previous word to be information about 
            
            should_be_value = words[index-1]

            logger.debug("expected value of %s", should_be_value)

            num2words = ['One', 'Two', 'Three', 'Four', 'Five', 'Six','Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve','Thirteen','Fourteen',  'Fifteen', 'Sixteen',  'Seventeen', 'Eighteen',  'Nineteen', 'Twenty']
            
            actual_value = -1

            
            if "+" in should_be_value:
                has_plus = True
                should_be_value = should_be_value.replace("+", "")

            if "-" in should_be_value:
                has_dash = True
                index = should_be_value.index("-")
                should_be_value = should_be_value[0:index]

            for idx, numwork in enumerate(num2words):
                if should_be_value == numwork.lower() or should_be_value == numwork.lower() + "+":
                    actual_value = idx + 1
                    logger.debug("a. actual value is matched to %s", actual_value)
                    break


            
            should_be_value = "".join([s for s in should_be_value if s.isdigit() or s == "."])
            logger.debug("should be value final %s", should_be_value)

            try: 
                if actual_value == -1:
                    if str(int(should_be_value)) == should_be_value:
                        actual_value = int(should_be_value)
                        logger.debug("b. actual value is matched to %s", actual_value)
            except ValueError as e: 
                # logger.critical(str(e))
                pass

            try: 
                if actual_value == -1:
                    actual_value = float(should_be_value)
                    logger.debug("c. actual value is matched to %s", actual_value)
            except ValueError as e: 
                # logger.critical(str(e))
                pass

            if actual_value == -1:
                actual_value = 0

            # logger.info("final actual value %s of type %s", actual_value , type(actual_value))
            # if its float value need to convert it to proper value example 2.1 means 2yr and 1month

            if isinstance(actual_value, float):
                if date_strings[dateIdx] == "year":
                    decimal_part, int_part = math.modf(actual_value)
                    final_days += day_map[dateIdx] * int_part + day_map[date_strings.index("month")] * decimal_part * 10 
                elif date_strings[dateIdx] == "month" or date_strings[dateIdx] == "week":
                    decimal_part, int_part = math.modf(actual_value)
                    final_days += day_map[dateIdx] * int_part + day_map[date_strings.index("day")] * decimal_part * 10
                else:
                    final_days += day_map[dateIdx] * actual_value

            else:
                final_days += day_map[dateIdx] * actual_value

            

        else:
            # logger.debug("not match %s ", date_str)
            pass


    # logger.info("%s ======================= %s days ", exp_str, final_days)
    return final_days, has_plus, has_dash   

def get_exp_display_range():
    return {
        "Less Than 1year" : {
            "min" : 0,
            "max" : 365,
            "sub_range" : {
                "Less than 6 months" : {
                    "min" : 0,
                    "max" : 31 * 6,
                },
                "6 months to 1year" : {
                    "min" : 31 * 6,
                    "max" : 365,
                }
            }
        },
        "1year to 5year" : {
            "min" : 365,
            "max" : 365 * 5,
            "sub_range" : {
                "1year to 2year" : {
                    "min" : 365,
                    "max" : 365*2,
                },
                "2year to 3year" : {
                    "min" : 365*2,
                    "max" : 365*3,
                },
                "3year to 4year" : {
                    "min" : 365 * 3,
                    "max" : 365 * 4,
                },
                "4year to 5year" : {
                    "min" : 365*4,
                    "max" : 365*5,
                },
            }
        },
        "5year to 10year" : {
            "min" : 365 * 5,
            "max" : 365 * 10,
            "sub_range" : {
                "5year to 6year" : {
                    "min" : 365 * 5,
                    "max" : 365 * 5,
                },
                "6year to 7year" : {
                    "min" : 365*6,
                    "max" : 365*7,
                },
                "7year to 8year" : {
                    "min" : 365 * 7,
                    "max" : 365 * 8,
                },
                "8year to 9year" : {
                    "min" : 365*8,
                    "max" : 365*9,
                },
            }
        },
        "10years+" : {
            "min" : 365 * 10,
            "max" : 365 * 1000
        }
    }

def getExperianceRange(exp_map):
    ranges = get_exp_display_range()

    for key in exp_map:
        exp = exp_map[key]
        for idx in ranges:
            if "count" not in ranges[idx]:
                ranges[idx]["count"] = 0
                ranges[idx]["children"] = []
                
            min_r = ranges[idx]["min"]
            max_r = ranges[idx]["max"]

            if exp >= min_r and exp < max_r:
                ranges[idx]["count"] += 1
                ranges[idx]["children"].append({
                    key: exp
                })

                if "sub_range" in ranges[idx]:
                    for subran in ranges[idx]["sub_range"]:
                        if "count" not in ranges[idx]["sub_range"][subran]:
                            ranges[idx]["sub_range"][subran]["count"] = 0
                            ranges[idx]["sub_range"][subran]["children"] = []

                        ranges[idx]["sub_range"][subran]["count"] += 1
                        ranges[idx]["sub_range"][subran]["children"].append({
                            key: exp
                        })




        
            
    # logger.info(ranges)

    return ranges

def getCourseDict():
    return {
        "10+2" : [],
        "diploma" : ["pg"],
        "bachelor": [
                "Bachelor of Agriculture:B.Sc.Agri",
                "Bachelor of Architecture:B.Arch",
                "Bachelor of Arts:B.A",
                "Bachelor of Ayurvedic Medicine & Surgery:B.A.M.S",
                "Bachelor of Business Administration:B.B.A",
                "Bachelor of Commerce:B.Com",
                "Bachelor of Computer Applications:B.C.A",
                "Bachelor of Computer Science:B.Sc",
                "Bachelor of Dental Surgery:B.D.S",
                "Bachelor of Design:B.Des:B.D",
                "Bachelor of Education:B.Ed",
                "Bachelor of Engineering:Bachelor of Technology:B.E:B.Tech",
                "Bachelor of Fine Arts:BFA:BVA",
                "Bachelor of Fisheries Science:B.F.Sc:Fisheries",
                "Bachelor of Home Science:Home Science",
                "Bachelor of Homeopathic Medicine and Surgery:B.H.M.S",
                "Bachelor of Laws:L.L.B",
                "Bachelor of Library Science:B.Lib",
                "Bachelor of Mass Communications:B.M.C:B.M.M",
                "Bachelor of Medicine and Bachelor of Surgery:M.B.B.S",
                "Bachelor of Nursing:Nursing",
                "Bachelor of Pharmacy:B.Pharm",
                "Bachelor of Physical Education:B.P.Ed",
                "Bachelor of Physiotherapy:B.P.T",
                "Bachelor of Science:B.Sc",
                "Bachelor of Social Work:BSW",
                "Bachelor of Veterinary Science & Animal Husbandry:B.V.Sc"
        ],
        "master": [
            "Doctor of Medicine:M.D",
            "Doctor of Medicine in Homoeopathy:Homoeopathy",
            "Master in Home Science:Home Science",
            "Master of Architecture:M.Arch",
            "Master of Arts:M.A",
            "Master of Business Administration:M.B.A.",
            "Master of Chirurgiae:M.Ch",
            "Master of Commerce:M.Com",
            "Master of Computer Applications:M.C.A",
            "Master of Dental Surgery:M.D.S",
            "Master of Design:M.Des",
            "Master of Education:M.Ed",
            "Master of Engineering:Master of Technology:M.E:M.Tech",
            "Master of Fine Arts:MFA:MVA",
            "Master of Fishery Science:M.F.Sc:Fisheries",
            "Master of Laws:L.L.M",
            "Master of Library Science:M.Lib",
            "Master of Mass Communications:M.M.C:M.M.M",
            "Master of Pharmacy:M.Pharm",
            "Master of Philosophy:M.Phil",
            "Master of Physical Education:M.P.Ed:M.P.E",
            "Master of Physiotherapy:M.P.T",
            "Master of Science:M.Sc",
            "Master of Science in Agriculture:Agriculture",
            "Master of Social Work:M.S.W",
            "Master of Surgery:M.S",
            "Master of Veterinary Science:M.V.Sc"],
        "doctorate" : [
            "Doctor of Pharmacy:Pharm.D",
            "Doctor of Philosophy:Ph.D",
            "Doctorate of Medicine:D.M"
        ]
    }

def generate_ngrams(s, n):
    # Convert to lowercases
    s = s.lower()
    
    # Replace all none alphanumeric characters with spaces
    # s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    
    # Break sentence in the token, remove empty tokens
    tokens = [token for token in s.split(" ") if token != ""]
    
    # Use the zip function to help us generate n-grams
    # Concatentate the tokens into ngrams and return
    ngrams = zip(*[tokens[i:] for i in range(n)])
    return [" ".join(ngram) for ngram in ngrams]


def matchCourse(education):
    
    org_edu = education
    education = education.replace("("," ")
    education = education.replace(")"," ")
    education = education.replace(","," ")
    education = re.sub(' +', ' ', education)

    education = education.replace(".","").lower()
    # logger.info("looking at %s", education)

    edu_grams = []
    edu_grams.append(education)
    edu_grams.extend(generate_ngrams(education, 1))
    edu_grams.extend(generate_ngrams(education, 2))
    edu_grams.extend(generate_ngrams(education, 3))

    max_ratio = 0
    final_course = {}
    exact_match = []

    courses_dict = getCourseDict()
    for edu in edu_grams:
      # print(edu)
      for key in courses_dict.keys():
        logger.debug("main sub %s", key)
        courses = courses_dict[key]
        for courseIdx, course in enumerate(courses):
          course = course.lower()
          course = course.split(":")
          
          for c in course:
            c = c.replace(".","")
            ratio = fuzz.ratio(c, edu)
            if ratio > 85:
              logger.debug("%s ratio = %s and %s", ratio, c, edu)
              if ratio > max_ratio:
                max_ratio = ratio
                final_course = {
                    "idx" : courseIdx,
                    "level" : key,
                    "edu": c,
                    "full" : courses[courseIdx]
                }

            if ratio == 100:
              found = False
              for match in exact_match:
                if match["key"] == key and match["idx"] == courseIdx:
                  found = True
                  break

              if found:
                exact_match.append({
                      "idx" : courseIdx,
                      "level" : key,
                      "edu": c,
                      "full" : courses[courseIdx]
                  })


    if len(exact_match) > 0:
      final_course = exact_match
    else:
      if "idx" in final_course:
        final_course = [final_course]
      else:
        final_course = []

    if len(final_course) == 0:
      # doing wide match
      for key in courses_dict.keys():
        if key.lower() in education:
          final_course = [{
              "level": key.lower()
          }]




    # logger.info("%s =========================================== %s", org_edu, final_course)

    return final_course

def get_passout_year(year_string):
  years = re.findall(r'\d{4}', year_string)
  print(year_string, " xxxx" , years)
  
  years_short = re.findall(r'-\d{2}\b', year_string) # to match something like -20, 2020-21
  if len(years_short) > 0:
    print(year_string, "xxx" , years_short)
    for yshort in years_short:
      yshort = yshort.replace("-", "20")
      years.append(yshort)
      
  max_year = -1
  for year in years:
    if int(year) > max_year:
      max_year = int(year)
  
  return max_year

def getPassoutYearFilters(passout_map):
    passout_filter = {}
    for key in passout_map:
        passout_year = passout_map[key]
        max_year = get_passout_year(passout_year)
        print("max year", max_year)
        if max_year != -1:
            if max_year not in passout_filter:
                passout_filter[max_year] = {
                    "count" : 0,
                    "children" : []
                }
            
            passout_filter[max_year]["count"] += 1
            passout_filter[max_year]["children"].append(key)

    return {k: v for k, v in sorted(passout_filter.items(), key=lambda item: item[1]["count"])}

def getGenderFilter(gender_map):
    gender_filter = {}
    for key in gender_map:
        gender = gender_map[key]
        if gender not in gender_filter:
            gender_filter[gender] = {
                "count" : 0,
                "children" : []
            }
        
        gender_filter[gender]["count"] += 1
        gender_filter[gender]["children"].append(key)

    return {k: v for k, v in sorted(gender_filter.items(), key=lambda item: item[1]["count"])}

def getEducationFilters(education_map):
    edu_filter = {}

    for key in education_map:
        edus = education_map[key]
        for edu in edus:
            final_course = matchCourse(edu)
            if len(final_course) > 0:
                final_course = final_course[0]

                if "level" in final_course:
                    full = final_course["level"]
                    display = full.split(":")[-1]
                    if display not in edu_filter:
                        edu_filter[display] = {
                            "count" : 0,
                            "children" : []
                        }

                    if key not in edu_filter[display]["children"]:
                        edu_filter[display]["count"] += 1
                        edu_filter[display]["children"].append(key)

                if "full" in final_course:
                    full = final_course["full"]
                    display = full.split(":")[-1]
                    if display not in edu_filter:
                        edu_filter[display] = {
                            "count" : 0,
                            "children" : []
                        }

                    if key not in edu_filter[display]["children"]:
                        edu_filter[display]["count"] += 1
                        edu_filter[display]["children"].append(key)
        
        
    # logger.info(edu_filter)

    return edu_filter


def designation(wrkExpList , wrkExpIdxMap):
    total_count = 0
    workCorpusIdxMap = {}
    work_corpus = {}
    for idx, wrkExp in enumerate(wrkExpList):
        wrkExp = re.sub('[^a-zA-Z0-9\n\.]', ' ', wrkExp)
        wrkExp = wrkExp.lower()
        wrkExp = re.sub(' +', ' ', wrkExp)
        wrkExp = wrkExp.strip()
        # words = wrkExp.split(" ")
        # for word in words:
        if wrkExp not in work_corpus:
            work_corpus[wrkExp] = 0

        if wrkExp not in workCorpusIdxMap:
            workCorpusIdxMap[wrkExp] = []

        workCorpusIdxMap[wrkExp].append(wrkExpIdxMap[idx])

        work_corpus[wrkExp] += 1
        total_count += 1

    work_corpus = {k: v for k, v in sorted(work_corpus.items(), key=lambda item: -1 * item[1])}

    # logger.info(work_corpus)
    merged_data = {}

    already_merged = []

    for idx, workExp in enumerate(work_corpus):
    
        if idx in already_merged:
            continue
        
        foundMatch = False
        if workExp not in merged_data:
            merged_data[workExp] = {
                'count' : work_corpus[workExp],
                'merge' : [],
                "children" : workCorpusIdxMap[workExp]
            }
        for idx2, workExp2 in enumerate(work_corpus):
            if idx >= idx2:
                continue

            if idx2 in already_merged:
                continue

            if workExp.lower() in workExp2.lower():
                already_merged.append(idx)
                foundMatch = True

                merged_data[workExp]["merge"].append(workExp2)
                merged_data[workExp]["count"] += work_corpus[workExp2]
                merged_data[workExp]["children"].extend(workCorpusIdxMap[workExp2])
                merged_data[workExp]["children"] = list(set(merged_data[workExp]["children"]))
                merged_data[workExp]["count"] = len(merged_data[workExp]["children"])

            else:
                if len(workExp2.split(" ")) == 1:
                    # single word
                    if workExp2.lower() in workExp.lower():
                        already_merged.append(idx2)
                        foundMatch = True
                        merged_data[workExp]["merge"].append(workExp2)
                        merged_data[workExp]["count"] += work_corpus[workExp2]
                        merged_data[workExp]["children"].extend(workCorpusIdxMap[workExp2])
                        merged_data[workExp]["children"] = list(set(merged_data[workExp]["children"]))
                        merged_data[workExp]["count"] = len(merged_data[workExp]["children"])

                    for idx3, workExp3 in enumerate(work_corpus):
                        if idx3 <= idx2:
                            continue

                        if idx3 in already_merged:
                            continue

                        if workExp2.lower() in workExp3.lower():
                            already_merged.append(idx3)
                            foundMatch = True

                            merged_data[workExp]["merge"].append(workExp3)
                            merged_data[workExp]["count"] += work_corpus[workExp3]
                            merged_data[workExp]["children"].extend(workCorpusIdxMap[workExp3])
                            merged_data[workExp]["children"] = list(set(merged_data[workExp]["children"]))
                            merged_data[workExp]["count"] = len(merged_data[workExp]["children"])


        if not foundMatch:
            pass

    final_count = 0
    for wrk in merged_data:
        final_count += merged_data[wrk]["count"]

    # logger.info("final count %s", final_count)  
    # logger.info("total count %s", total_count)
    # logger.info(json.dumps(merged_data, indent=True))


    threshold = 5
    other = {
        "count" : 0,
        "merge" : [],
        "children" : []
    }
    if len(merged_data) < 10:
        threshold = 1

    combine_merged_data = {}

    for workExp in merged_data:
        data = merged_data[workExp]
        if data["count"] < threshold:
            other["count"] += data["count"]
            other["merge"].extend(data["merge"])
            other["children"].extend(data["children"])
        else:
            combine_merged_data[workExp] = data

    combine_merged_data["other"] = other

    # logger.info(json.dumps(combine_merged_data, indent=True))


    return combine_merged_data

    
def location(gpeList, gpeIdxMap):

    gpe_corpus = {}

    gpeCorpusIdxMap = {}

    for idx, gpe in enumerate(gpeList):
        gpe = re.sub('[^a-zA-Z0-9\n\.]', ' ', gpe)
        gpe = gpe.lower()
        gpe = re.sub(' +', ' ', gpe)
        if gpe not in gpe_corpus:
            gpe_corpus[gpe] = 0
        
        gpe_corpus[gpe] += 1

        if gpe not in gpeCorpusIdxMap:
            gpeCorpusIdxMap[gpe] = []

        gpeCorpusIdxMap[gpe].append(gpeIdxMap[idx])

    gpe_corpus = {k: v for k, v in sorted(gpe_corpus.items(), key=lambda item: -1 * item[1])}

    # logger.info(gpe_corpus)

    merged_data = {}

    already_merged = []

    for idx, gpe in enumerate(gpe_corpus):
    
        if idx in already_merged:
            continue
        
        foundMatch = False
        if gpe not in merged_data:
            merged_data[gpe] = {
                'count' : gpe_corpus[gpe],
                'merge' : [],
                "children" : gpeCorpusIdxMap[gpe]
            }
        for idx2, gpe2 in enumerate(gpe_corpus):
            if idx >= idx2:
                continue

            if gpe.lower() in gpe2.lower():
                already_merged.append(idx2)
                foundMatch = True

                merged_data[gpe]["merge"].append(gpe2)
                merged_data[gpe]["count"] += gpe_corpus[gpe2]
                merged_data[gpe]["children"].extend(gpeCorpusIdxMap[gpe2])
                merged_data[gpe]["children"] = list(set(merged_data[gpe]["children"]))
                merged_data[gpe]["count"] = len(merged_data[gpe]["children"])

            else:
                if len(gpe2.split(" ")) == 1:
                    # single word
                    if gpe2.lower() in gpe.lower():
                        already_merged.append(idx2)
                        foundMatch = True
                        merged_data[gpe]["merge"].append(gpe2)
                        merged_data[gpe]["count"] += gpe_corpus[gpe2]
                        merged_data[gpe]["children"].extend(gpeCorpusIdxMap[gpe2])
                        merged_data[gpe]["children"] = list(set(merged_data[gpe]["children"]))
                        merged_data[gpe]["count"] = len(merged_data[gpe]["children"])

                        for idx3, gpe3 in enumerate(gpe_corpus):
                            if idx3 <= idx2:
                                continue

                            if gpe2.lower() in gpe3.lower():
                                already_merged.append(idx3)
                                foundMatch = True

                                merged_data[gpe]["merge"].append(gpe3)
                                merged_data[gpe]["count"] += gpe_corpus[gpe3]
                                merged_data[gpe]["children"].extend(gpeCorpusIdxMap[gpe3])
                                merged_data[gpe]["children"] = list(set(merged_data[gpe]["children"]))
                                merged_data[gpe]["count"] = len(merged_data[gpe]["children"])



        if not foundMatch:
            pass



    threshold = 5
    other = {
        "count" : 0,
        "merge" : [],
        "children" : []
    }
    if len(merged_data) < 10:
        threshold = 1

    combine_merged_data = {}

    for workExp in merged_data:
        data = merged_data[workExp]
        if data["count"] < threshold:
            other["count"] += data["count"]
            other["merge"].extend(data["merge"])
            other["children"].extend(data["children"])
        else:
            combine_merged_data[workExp] = data

    combine_merged_data["other"] = other

    # logger.info(json.dumps(combine_merged_data, indent=True))


    return combine_merged_data

def get_dob_year(year_string):
  years = re.findall(r'\d{4}', year_string)
  print(year_string, " xxxx" , years)
  
  max_year = 99999
  for year in years:
    if int(year) < max_year:
      max_year = int(year)
  
  return max_year

def get_dob_filter(dob_map):
    dob_filter = {}
    for key in dob_map:
        dob_str = dob_map[key]
        dob = get_dob_year(dob_str)
        if dob == 99999:
            continue
        
        if dob not in dob_filter:
            dob_filter[dob] = {
                "count" : 0,
                "children" : []
            }
        
        dob_filter[dob]["count"] += 1
        dob_filter[dob]["children"].append(key)

    return {k: v for k, v in sorted(dob_filter.items(), key=lambda item: item[1]["count"])}
