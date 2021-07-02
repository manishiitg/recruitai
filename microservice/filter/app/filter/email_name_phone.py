import re
from email_validator import validate_email, EmailNotValidError, EmailSyntaxError, EmailUndeliverableError
from app.logging import logger
from bson.objectid import ObjectId
from collections import OrderedDict
from app.publishgender import sendBlockingMessage as getGenderMessage


def pre_process_email(Email):
    Email = Email.strip().lower()
    # Validate.
    if ":-" in Email:
        index = Email.index(":-")
        Email = Email[index+1:]

    if "-" in Email:
        index = Email.index("-")
        Email = Email[index+1:]

    if ":" in Email:
        index = Email.index(":")
        Email = Email[index+1:]

    if ".." in Email:
        Email = Email.replace("..", ".")

    if "\\n" in Email:
        Email = Email.replace("\n", "")

    if "\n" in Email:
        Email = Email.replace("\n", "")

    if "@gmail.co" in Email and "@gmail.com" not in Email:
        Email = Email.replace("@gmail.co", "@gmail.com")

    if "@outlook.co" in Email and "@outlook.com" not in Email:
        Email = Email.replace("@outlook.co", "@outlook.com")

    if "@hotmail.co" in Email and "@hotmail.com" not in Email:
        Email = Email.replace("@hotmail.co", "@hotmail.com")

    if "@yahoo.co" in Email and "@yahoo.com" not in Email:
        Email = Email.replace("@yahoo.co", "@yahoo.com")

    if "@gmail.com.co" in Email:
        Email = Email.replace("@gmail.com.co", "@gmail.com")

    if "@gmail.com/" in Email:
        rindex = Email.rindex("/")
        Email = Email[:rindex]

    if ".@" in Email:
        Email = Email.replace(".@", "@")

    if "@" not in Email:
        if "gma" in Email:
            Email = Email.replace("gma", "@gma")
        if "yaho" in Email:
            Email = Email.replace("yaho", "@yaho")
        if "outl" in Email:
            Email = Email.replace("outl", "@outl")

    if len(Email.strip()) < 2:
        return Email
    # logger.info("XXX", Email, len(Email))
    # jagritgupta_manoj@srmuniv.edu.in\n

    if Email[-1] == "\n":
        Email = Email[:-1]

    if not Email[-1].isalnum():
        Email = Email[:-1]

    if not Email[0].isalnum():
        Email = Email[1:]

    return Email


def handleEmailException(exp, error, Email, row):
    # 1993 singh007pravesh@gmail.com
    if "invalid characte" in error:
        Email = str(Email.encode('ascii', 'ignore'))
        if "b'" in Email:
            Email = Email.replace("b'", "").replace("'", "")
        if 'b"' in Email:
            Email = Email.replace('b"', "").replace('"', "")

        if " " in Email and Email.count("@") == 1:
            # learning. gangadhargondi@outlook.com
            min_len = 99
            for s in Email.split(" "):
                if len(s) < min_len and len(s) != 0:
                    min_len = len(s)

            if min_len < 15:
                Email = "".join(Email.split(" "))
                try:
                    valid = validate_email(Email)
                    return valid.email
                except EmailNotValidError as e:
                    logger.info("88")
                    logger.info(Email)
                    logger.info(row["_id"])
                    logger.info(str(e))
                    logger.info(e)
                    logger.info("*******************")

    if "The email address" in error:
        # aafrinnaaz07jan @gmail.com
        # a nsaribomik@gmail.com
        if " @" in Email:
            Email = Email.replace(" @", "@")
            try:
                valid = validate_email(Email)
                return valid.email
            except EmailNotValidError as e:
                logger.info("1")
                logger.info(Email)
                logger.info(row["_id"])
                logger.info(str(e))
                logger.info(e)
                logger.info("*******************")

        # mohdtauheed534@gmail.com mohd786tauheed@gmail.com
        # mohdtauheed534@gmail.com@gmail.com
        if Email.count("@") > 1:
            if " " in Email.strip():
                Emails = Email.split(" ")
                valid_emails = []
                for email in Emails:
                    email = pre_process_email(email)
                    try:
                        valid = validate_email(email)
                        valid_emails.append(valid.email)
                        # need to update code here for two valid emails
                    except EmailNotValidError as e:
                        logger.info("2")
                        logger.info(email)
                        logger.info(row["_id"])
                        logger.info(str(e))
                        logger.info(e)
                        logger.info("*******************")
                        logger.info(str(e))

                return valid_emails

            else:
                lindex = Email.rindex("@")
                Email = Email[:lindex]
                try:
                    valid = validate_email(Email)
                    return valid.email
                    # need to update code here for two valid emails
                except EmailNotValidError as e:
                    logger.info("3")
                    logger.info(Email)
                    logger.info(row["_id"])
                    logger.info(str(e))
                    logger.info(e)
                    logger.info("*******************")
                    logger.info(str(e))

    if "The domain name" in error:
        if "@g" in Email:
            Email = Email.split("@")
            Email = Email[0] + "@gmail.com"
            try:
                valid = validate_email(Email)
                return valid.email
            except EmailNotValidError as e:
                logger.info("4")
                logger.info(Email)
                logger.info(row["_id"])
                logger.info(str(e))
                logger.info(e)
                logger.info("*******************")
                logger.info(str(e))

        if ".i" in Email:
            Email = Email.replace(".i", ".in")
            try:
                valid = validate_email(Email)
                return valid.email
            except EmailNotValidError as e:
                logger.info("5")
                logger.info(Email)
                logger.info(row["_id"])
                logger.info(str(e))
                logger.info(e)
                logger.info("*******************")
                logger.info(str(e))

    logger.info("6")
    logger.info(Email)
    logger.info(row["_id"])
    logger.info(str(exp))
    logger.info("*******************")
    return None


def extract_valid_email(Email, row):
    if Email is None:
        return None
    try:
        Email = pre_process_email(Email)

        valid = validate_email(Email, check_deliverability=True)
        # Update with the normalized form.
        if Email != valid.email:
            logger.info("org email %s", Email)
            logger.info("valid email %s", valid.email)
            logger.info("domain %s", valid.domain)
            logger.info("*******************")

        return valid.email
    except EmailUndeliverableError as e:
        error = str(e)
        logger.info("----------------error")
        return None
    except EmailSyntaxError as e:
        error = str(e)
        return handleEmailException(e, error, Email, row)
    except EmailNotValidError as e:
        # email is not valid, exception message is human-readable
        error = str(e)
        return handleEmailException(e, error, Email, row)


def email_check_db(row, db):
    if "cvParsedInfo" not in row:
        return None
    if "finalEntity" in row["cvParsedInfo"]:

        if "sender_mail" in row:
            sender_mail = row["sender_mail"]
        else:
            sender_mail = ""

        logger.info("=================")
        logger.info(sender_mail)
        final_entity_email = []
        qa_parse_email = []

        if "Email" in row["cvParsedInfo"]["finalEntity"]:
            Email = row["cvParsedInfo"]["finalEntity"]["Email"]["obj"]
            Email = extract_valid_email(Email, row)
            if Email is None:
                pass
            else:
                if isinstance(Email, list):
                    # logger.info("finalentity", Email)
                    final_entity_email = Email
                    db.emailStored.update_one({
                        '_id': ObjectId(str(row["_id"]))
                    }, {
                        "$set": {
                            "cvParsedInfo.finalEntity.Email.obj": " ".join(Email)
                        }
                    })
                else:
                    # logger.info("finalentity", Email)
                    final_entity_email.append(Email)
                    db.emailStored.update_one({
                        '_id': ObjectId(str(row["_id"]))
                    }, {
                        "$set": {
                            "cvParsedInfo.finalEntity.Email.obj": Email
                        }
                    })
        qa_parse_resume = None
        if "qa_parse_resume" in row["cvParsedInfo"]:
            qa_parse_resume = row["cvParsedInfo"]["qa_parse_resume"]
        else:
            if "qa_fast_search_space" in row["cvParsedInfo"]:
                qa_parse_resume = row["cvParsedInfo"]["qa_fast_search_space"]

        if qa_parse_resume:
            for question_key in qa_parse_resume:
                if "personal_" in question_key:
                    sections = qa_parse_resume[question_key]
                    if not isinstance(sections, list):
                        sections = [sections] # qa fast search space
                    for section in sections:
                        if "tags" in section:
                            tags = section["tags"]
                            for tag in tags:
                                if tag["label"] == "Email":
                                    value = tag["text"]
                                    Email = extract_valid_email(value, row)
                                    if Email is None:
                                        pass
                                    else:
                                        if isinstance(Email, list):
                                            # logger.info("qa parse", Email)
                                            qa_parse_email.extend(Email)
                                        else:
                                            # logger.info("qa parse", Email)
                                            qa_parse_email.append(Email)
        

        qa_parse_email = list(set(qa_parse_email))
        final_entity_email = list(set(final_entity_email))
        if sender_mail and len(sender_mail) > 0:
            sender_mail = sender_mail.lower()
            other_emails = []
            for email in final_entity_email:
                if email == sender_mail:
                    pass
                elif email in sender_mail:
                    pass
                else:
                    other_emails.append(email)

            for email in qa_parse_email:
                if email == sender_mail:
                    pass
                elif email in sender_mail:
                    pass
                else:
                    other_emails.append(email)

                other_emails = list(set(other_emails))
                logger.info("different %s", other_emails)
                if len(other_emails) > 0:
                    db.emailStored.update_one({
                        '_id': ObjectId(str(row["_id"]))
                    }, {
                        "$set": {
                            "cvParsedInfo.finalEntity.additional-Email": other_emails
                        }
                    })
        else:
            if len(qa_parse_email) > 0:
                if len(qa_parse_email) >= 1:
                    logger.info("proimary email %s", qa_parse_email[0])
                    logger.info("second email %s", qa_parse_email[1:])
                    db.emailStored.update_one({
                        '_id': ObjectId(str(row["_id"]))
                    }, {
                        "$set": {
                            "sender_mail": qa_parse_email[0],
                            "sender_mail_ai": 'qa_parse',
                            "cvParsedInfo.finalEntity.additional-Email": qa_parse_email[1:]
                        }
                    })
                elif len(qa_parse_email) == 1:
                    logger.info("proimary email %s", qa_parse_email[0])
                    db.emailStored.update_one({
                        '_id': ObjectId(str(row["_id"]))
                    }, {
                        "$set": {
                            "sender_mail": qa_parse_email[0],
                            "sender_mail_ai": 'qa_parse'
                        }
                    })

            else:
                if len(final_entity_email) >= 1:
                    logger.info("proimary email %s", final_entity_email[0])
                    logger.info("second email %s", final_entity_email[1:])
                    db.emailStored.update_one({
                        '_id': ObjectId(str(row["_id"]))
                    }, {
                        "$set": {
                            "sender_mail": final_entity_email[0],
                            "sender_mail_ai": 'final_entity',
                            "cvParsedInfo.finalEntity.additional-Email": final_entity_email[1:]
                        }
                    })
                elif len(final_entity_email) == 1:
                    logger.info("proimary email %s", final_entity_email[0])
                    db.emailStored.update_one({
                        '_id': ObjectId(str(row["_id"]))
                    }, {
                        "$set": {
                            "sender_mail": final_entity_email[0],
                            "sender_mail_ai": 'final_entity'
                        }
                    })

        id = str(row["_id"])
        logger.info(f"================={id}")


def process_name(row, db, account_name, account_config):
    if "cvParsedInfo" not in row:
        return None

    if "finalEntity" in row["cvParsedInfo"]:

        if "from" in row:
            name = row["from"]
        else:
            name = ""

        if name is None:
            name = ""

        # if len(name) > 0:
        #     return
        # need to replace name from resume. many times from name is not actual name of user

        logger.info("=================")
        logger.info(name)
        final_entity_email = []
        qa_parse_email = []

        final_name = ""
        if "PERSON" in row["cvParsedInfo"]["finalEntity"]:
            if "PERSON" in row["cvParsedInfo"]["finalEntity"]:
                if "obj" in row["cvParsedInfo"]["finalEntity"]["PERSON"]:
                    Name = row["cvParsedInfo"]["finalEntity"]["PERSON"]["obj"]
                # logger.info("final entity name ", Name)
                    final_name = Name

        qa_final_name = None
        if "answer_map" in row["cvParsedInfo"]:
            answer_map = row['cvParsedInfo']["answer_map"]
            if "personal_name" in answer_map:
                personal_name = answer_map["personal_name"]
                if "answer" in personal_name:
                    qa_final_name = personal_name["answer"]
                    logger.critical("qa final name %s actual final name %s", qa_final_name, final_name)
                    if len(final_name) > 0:
                        # logger.critical("h1")
                        if final_name.lower() in qa_final_name.lower() or qa_final_name.lower() in final_name.lower() or final_name.lower() == qa_final_name.lower():
                            # this means name are similar so will take the longer name
                            if len(final_name) > len(qa_final_name):
                                # logger.critical("h2")
                                pass
                            else:
                                final_name = qa_final_name
                                # logger.critical("h3")
                        else:
                            # will prefer qa over ner if name not matching at all
                            final_name = qa_final_name                            
                            # logger.critical("h4")
                    else:
                        # logger.critical("h5")
                        final_name = personal_name["answer"]
        # qa_parse_resume = None
        # if "qa_parse_resume" in row["cvParsedInfo"]:
        #     qa_parse_resume = row["cvParsedInfo"]["qa_parse_resume"]
        # else:
        #     if "qa_fast_search_space" in row["cvParsedInfo"]:
        #         qa_parse_resume = row["cvParsedInfo"]["qa_fast_search_space"]

        # if qa_parse_resume:
        #     for question_key in qa_parse_resume:
        #         if "personal_" in question_key:
        #             sections = qa_parse_resume[question_key]
        #             if not isinstance(sections, list):
        #                 sections = [sections] # qa fast search space
        #             for section in sections:
        #                 if "tags" in section:
        #                     tags = section["tags"]
        #                     for tag in tags:
        #                         if tag["label"] == "PERSON":
        #                             value = tag["text"].strip()
        #                             # logger.info("qa parse", value)
        #                             if len(value) > 0:
        #                                 if qa_final_name is None:
        #                                     final_name = value
        #                                     qa_final_name = value

        if final_name:
            if "@" in final_name:
                names = final_name.split(" ")
                new_names = []
                for n in names:
                    if "@" not in n:
                        new_names.append(n)

                final_name = " ".join(new_names)

            final_name = " ".join(
                list(OrderedDict.fromkeys(final_name.split(" "))))

        id = str(row["_id"])

        if len(final_name) > 0:
            gender  =  getGender(final_name, account_name, account_config)
            db.emailStored.update_one({
                "_id": ObjectId(id)
            }, {
                '$set': {
                    "from": final_name,
                    "finalEntity.gender" : gender,
                    # "org_name" : name  # no use of this because its called so many times the from and org_name will keep getting replaced
                }
            })
            logger.critical(f"================={id} and final name {final_name} and gender {gender}")


def parse_phone_string(Phone):
    vp = None
    if "," in Phone:
        new_phones = []
        for p in Phone.split(","):
            vp = validate_phone(p)
            if vp:
                new_phones.append(vp)
        return new_phones

    elif "|" in Phone:
        new_phones = []
        for p in Phone.split("|"):
            vp = validate_phone(p)
            if vp:
                new_phones.append(vp)
        return new_phones

    elif "/" in Phone:
        new_phones = []
        for p in Phone.split("/"):
            vp = validate_phone(p)
            if vp:
                new_phones.append(vp)
        return new_phones

    elif " " in Phone:
        phones = Phone.split(" ")
        is_not_valid = False
        for p in phones:
            if len(p.strip()) < 10:
                is_not_valid = True

        if is_not_valid:
            vp = validate_phone(Phone)
        else:
            new_phones = []
            for p in Phone.split(" "):
                vp = validate_phone(p)
                if vp:
                    new_phones.append(vp)
            return new_phones

    else:
        vp = validate_phone(Phone)

    return vp


def validate_phone(Phone):
    if "(+91)" in Phone:
        Phone = Phone.replace("(+91)", "")
    if "+91-" in Phone:
        Phone = Phone.replace("+91-", "")

    if "91+" in Phone:
        Phone = Phone.replace("91+", "")

    if "+91" in Phone:
        Phone = Phone.replace("+91", "")

    if "91-" in Phone:
        Phone = Phone.replace("91-", "")

    if Phone.startswith("91") and len(Phone.strip()) > 10:
        Phone = Phone.replace("91", "")

    if ":" in Phone:
        Phone = Phone[Phone.index(":") + 1:]
    
    if "." in Phone:
        Phone = Phone[Phone.index(".") + 1:]

    Phone = Phone.strip()
    if len(Phone) == 0:
        return None

    if Phone[0] == "0":
        Phone = Phone[1:]

    Phone = re.sub("[^0-9]", "", Phone)

    if len(Phone) == 10:
        return Phone
    else:
        return None


def fix_phone(row, db):
    if "cvParsedInfo" not in row:
        return None
    if "finalEntity" in row["cvParsedInfo"]:

        final_phone = []

        if "Phone" in row["cvParsedInfo"]["finalEntity"]:
            Phone = row["cvParsedInfo"]["finalEntity"]["Phone"]["obj"]
            p = parse_phone_string(Phone)
            if p:
                logger.info(f"valid phone {p} and original {Phone}")
                if isinstance(p, list):
                    final_phone.extend(p)
                else:
                    final_phone.append(p)
                pass
            else:
                logger.info(f"invalid phone no {Phone}")

        if "additional-Phone" in row["cvParsedInfo"]["finalEntity"]:
            Phones = row["cvParsedInfo"]["finalEntity"]["additional-Phone"]
            for Phone in Phones:
                p = parse_phone_string(Phone)
                if p:
                    logger.info(f"additional valid phone {p} and original {Phone}")
                    if isinstance(p, list):
                        final_phone.extend(p)
                    else:
                        final_phone.append(p)
                    pass
                else:
                    logger.info(f"additional invalid phone no {Phone}")

        qa_parse_resume = None
        if "qa_parse_resume" in row["cvParsedInfo"]:
            qa_parse_resume = row["cvParsedInfo"]["qa_parse_resume"]
        else:
            if "qa_fast_search_space" in row["cvParsedInfo"]:
                qa_parse_resume = row["cvParsedInfo"]["qa_fast_search_space"]

        if qa_parse_resume:
            for question_key in qa_parse_resume:
                if "personal_" in question_key:
                    sections = qa_parse_resume[question_key]
                    if not isinstance(sections, list):
                        sections = [sections] # qa fast search space
                    for section in sections:
                        if "tags" in section:
                            tags = section["tags"]
                            for tag in tags:
                                if tag["label"] == "Phone":
                                    Phone = tag["text"]
                                    p = parse_phone_string(Phone)
                                    if p:
                                        logger.info(
                                            f"qa parse valid phone {p} and original {Phone}")
                                        if isinstance(p, list):
                                            final_phone.extend(p)
                                        else:
                                            final_phone.append(p)
                                        pass
                                    else:
                                        logger.info(
                                            f"qa parse invalid phone no {Phone}")

        id = str(row["_id"])
        logger.info(f"================={id}")
        
        final_phone = list(OrderedDict.fromkeys(final_phone))
        if len(final_phone) > 0:
            if len(final_phone) == 1:
                db.emailStored.update_one({
                    "_id": ObjectId(id)
                }, {
                    '$set': {
                        "cvParsedInfo.finalEntity.Phone.obj": final_phone[0],
                        "cvParsedInfo.finalEntity.additional-Phone": []
                    }
                })
            else:
                db.emailStored.update_one({
                    "_id": ObjectId(id)
                }, {
                    '$set': {
                        "cvParsedInfo.finalEntity.Phone.obj": final_phone[0],
                        "cvParsedInfo.finalEntity.additional-Phone": final_phone[1:]
                    }
                })
        else:
            if "Phone" in row["cvParsedInfo"]["finalEntity"]:
                finalEntity = row["cvParsedInfo"]["finalEntity"]
                del finalEntity["Phone"]
                if "additional-Phone" in finalEntity:
                    del finalEntity["additional-Phone"]

                db.emailStored.update_one({
                    "_id": ObjectId(id)
                }, {
                    '$set': {
                        "cvParsedInfo.finalEntity": finalEntity
                    }
                })

        # break

def getGender(name, account_name, account_config):
    return getGenderMessage({
        "name" : name,
        "account_name" : account_name,
        "account_config" : account_config
    })