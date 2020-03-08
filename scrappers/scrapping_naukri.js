const puppeteer = require('puppeteer-extra')

// add stealth plugin and use defaults (all evasion techniques)
const StealthPlugin = require('puppeteer-extra-plugin-stealth')
puppeteer.use(StealthPlugin())
// var userAgent = require('user-agents');
// const StealthPlugin = require('puppeteer-extra-plugin-stealth')
// puppeteer.use(StealthPlugin())

var userAgent = require('user-agents');

const mongoose = require('mongoose');
const Schema = mongoose.Schema;

let CandidateScheme = new Schema({}, { strict: false });
let NaukriProgressScheme = new Schema({}, { strict: false });

let Candidate = mongoose.model('naukri_Candidate', CandidateScheme);
let NaukriProgress = mongoose.model('naukri_progress', NaukriProgressScheme);

var url = "mongodb://staging_recruit:staging_recruit@5.9.144.226:27017/staging_recruit";

mongoose.connect(url, { useNewUrlParser: true });

let db = mongoose.connection;

db.on('error', console.error.bind(console, 'MongoDB connection error:'));

// query = ["developer"]
// l = ["","Delhi","Mumbai%2C+Maharashtra","Bangalore%2C+Karnataka","Hyderabad%2C+Telangana","Chennai%2C+Tamil+Nadu","Pune%2C+Maharashtra"]


// query_index = 0
// location_index = 1

setTimeout(() => {
    console.log("auto restarted in 15min")
    process.exit(1)
}, (15 * 60 * 1000))

// # software developer - id :99


// Candidate.aggregate([
//     { "$group": { _id: "$extra_data.industry_name", count: { $sum: 1 } } },
//     { "$sort": { "count": -1 } }
// ]).then((ret) => {
//     console.log(ret)

// })

// return


//industries we have
// ['Security / Law Enforcement', 
// 'Chemicals / PetroChemical / Plastic / Rubber', 
// 'Office Equipment / Automation', 
// 'Education / Teaching / Training', 
// 'BPO / ITES', 'Real Estate / Property', 
// 'Semiconductors / Electronics', 
// 'Banking / Financial Services / Broking', 
// 'IT-Software / Software Services', 
// 'Courier / Transportation / Freight', 
// 'Water Treatment / Waste Management', 
// 'Architecture / Interior Design', 
// 'Food Processing', 
// 'Advertising / PR / MR / Events', 
// 'Auto / Auto Ancillary', 
// 'IT-Hardware & Networking',
//  'Oil and Gas / Power / Infrastructure / Energy', 
//  'Consumer Durables', 
//  'Hotels / Restaurants / Airlines / Travel', 
//  'Strategy /Management Consulting Firms', 
//  'Construction / Engineering / Cement / Metals', 
//  'Textiles / Garments / Accessories', 
//  'Pharma / Biotech / Clinical Research', 
//  'Recruitment', 
//  'Insurance', 
//  'KPO / Research /Analytics', 
//  'Telecom / ISP', 
//  'Ceramics /Sanitary ware', 
//  'Fresher / Trainee', 
//  'Internet / Ecommerce', 
//  'Medical / Healthcare / Hospital', 
//  'Electricals / Switchgears', 
//  'Media / Dotcom / Entertainment', 
//  'Glass', 
//  'FMCG / Foods / Beverage', 
//  'Industrial Products / Heavy Machinery', 
//  'Legal', 
//  'Agriculture / Dairy', 
//  'Paper', 
//  'Retail', 
//  'Facility Management', 
//  'Heat Ventilation Air Conditioning', 
//  'Tyres', 
//  'Shipping / Marine', 
//  'Other', 
//  'Steel',
//   'Wellness/Fitness/Sports', 
//   'Mining', 
//   'Export / Import', 
//   'Printing / Packaging', 
//   'Fertilizers / Pesticides', 
//   'Aviation / Aerospace Firm', 
//   'Defence / Government', 
//   'NGO / Social Services', 
//   'Brewery / Distillery', 
//   'Publishing', 
//   'Gems & Jewellery', 
//   'Animation']


// as per shine jobs
//IT software jobs
// Recritment 
// BPO/ CAll center
// Education Training JObs
// management consuting strategy jobs
// manufacturing jobs

//as per times jobs
//IT jobs
//manufacturing engineering
//banking finance
//BPO
//sales and marketing

//as per monsther
//HR
//Finance Accounts
//IT
//purchase and supply chain
//admin/secretary
//legal
//BPO kPo
//Marking
//Sales
//Others


//as per headhonchoes

//finance
//hr
//IT
//manufactring
//marking
//sales

// we have 3 things from my understanding
// a) industry : this can be like IT, Banking, Telecom, Engineering, Oil/Gas etc
// b) we have functions like IT, HR, Accounts, Marketing, Sales, Legal, Admin, Customer Service/BPO, Others.
// for every industry we have these functions. for a person who is in accounts can go into any of the above industries
// c) then we have role or designations these are specific to functions so we can HR Executive, Sales Excecutive etc
// d) we have have senior junior etc in this. fresher trainee etc

industry = [
    { "name": "IT Software Services", "naukri_id": 25 },
    { "name": "Banking Finance", "naukri_id": 14 },
    { "name": "Accounts", "naukri_id": 8 },
    { "name": "Manufacturing/Engg", "naukri_id": 3 },
    { "name": "BPO ITES", "naukri_id": 7 },
    { "name": "FMCG" },
    { "name": "Oil" },
    { "name": "Retail" },
    { "name": "Legal" }]

//looking at candidate cv's even maually its not possible to identify candidates based on this
//i think this would be more job based because any candidate in IT lets php can apply above indsutries






const wsChromeEndpointurl = 'ws://127.0.0.1:9222/devtools/browser/693ced97-06f2-4def-8286-038c82e4b0ef';

const sleep = (milliseconds) => {
    return new Promise(resolve => setTimeout(resolve, milliseconds))
}


async function get_page_data(browser, page, extra_data = {}, start_page = -1, start_page_index = 0, current_page = 0) {
    let hrefs = await page.$$eval('div.tup', ele => ele.length);
    console.log(hrefs)


    var functionToInject = function () {
        return [window.sid, window.searchTime];
    }

    var env_data = await page.evaluate(functionToInject); // <-- Just pass the function
    console.log(env_data); // outputs: Netscape

    if (current_page >= 10) {
        console.log("not parsing more than 4 pages for now ")
        return true
    }


    // await page.$$eval("a.p_l" , link => {
    //     console.log(link.href)
    // })
    // urls = []
    console.log("total resumes found", hrefs)
    if (hrefs > 0) {
        start_index = 0
        if (start_page != -1 && current_page < start_page) {
            start_index = hrefs
        }
        if (start_page != -1 && current_page == start_page) {
            start_index = start_page_index
        }
        console.log("start index ", start_index, " curent page ", current_page)
        for (i = start_index; i < hrefs; i++) {
            uname = await page.$eval('#u' + i, e => e.innerText)

            let existCandidate = await Candidate.findOne({ "uname": uname }).lean()
            if (existCandidate && existCandidate["extra_info"]) {
                //false because we are parsing new data now 
                console.log("candidate already exists, just updated extra data")
                extra_data["current_page"] = current_page
                extra_data["index"] = i
                if (!existCandidate["extra_data"]) {
                    existCandidate["extra_data"] = extra_data
                } else {
                    for (let key in extra_data) {
                        if (existCandidate["extra_data"][key] && existCandidate["extra_data"][key] != extra_data[key]) {
                            console.log("this key already exists", key)
                            existCandidate["extra_data"][key + "_" + i] = existCandidate["extra_data"][key]
                        }
                        existCandidate["extra_data"][key] = extra_data[key]
                    }
                }
                await Candidate.update({ "_id": existCandidate["_id"] }, existCandidate)
                continue
            }


            url = "https://freesearch.naukri.com/preview/preview?uname=" + uname + "&sid=" + env_data[0] + "&LT=" + env_data[1]
            console.log(url)
            // urls.push(url)

            const page2 = await browser.newPage();
            await page2.goto(url)

            // await page2.setRequestInterception(true);
            // page2.on('request', async request => {
            //     console.log(request.url(), "xxxx")
            // })

            data = await page2.evaluate(() => {
                key_skills = ""
                skDiv = document.querySelector(".grntxt")
                if (skDiv)
                    key_skills = skDiv.innerText

                extra_info = {}
                summary = ""
                workExp = []
                education = []
                projects = []
                el = document.querySelector(".w338")
                if (el) {
                    el.querySelectorAll(":scope > li").forEach(el => {
                        txt = el.innerText
                        key = txt.split(":")[0]
                        value = txt.split(":")[1]
                        key = key.replace(" ", "-").replace(".", "")
                        extra_info[key] = value
                    })
                }
                if (document.querySelector(".pr5")) {
                    extra_info["name"] = document.querySelector(".pr5").innerText
                }

                el = document.querySelector(".w300")
                if (el) {
                    el.querySelectorAll(":scope > li").forEach(el => {
                        txt = el.innerText
                        key = txt.split(":")[0]
                        value = txt.split(":")[1]
                        key = key.replace(" ", "-").replace(".", "")
                        extra_info[key] = value
                    })
                }
                document.querySelectorAll(".section").forEach((el) => {
                    heading = el.querySelector(":scope > h2").innerText
                    if (heading.indexOf("Summary") != -1) {
                        summary = el.querySelector(":scope > p").innerText
                    }
                })
                document.querySelectorAll(".nSec").forEach((el) => {
                    heading = el.querySelector(":scope > h2").innerText
                    if (heading.indexOf("Summary") != -1) {
                        summary = el.querySelector(":scope > p").innerText
                    } else if (heading.indexOf("Work Experience") != -1) {
                        lis = el.querySelectorAll(":scope > ul > li")
                        lis.forEach((li) => {
                            if (li.querySelector(":scope > p > strong"))
                                company_name = li.querySelector(":scope > p > strong").innerText
                            else
                                company_name = ""
                            if (li.querySelectorAll(":scope > p > .f14")[2]) {
                                designation = li.querySelectorAll(":scope > p > .f14")[1].innerText
                                date = li.querySelectorAll(":scope > p > .f14")[2].innerText
                            } else if (li.querySelectorAll(":scope > p > .f14")[1]) {
                                designation = ""
                                date = li.querySelectorAll(":scope > p > .f14")[1].innerText
                            } else {
                                designation = ""
                                date = ""
                            }
                            if (li.querySelector(":scope > p > .cls"))
                                desc = li.querySelector(":scope > p > .cls").innerText
                            else
                                desc = ""

                            workExp.push({
                                company_name: company_name,
                                designation: designation,
                                date: date,
                                desc: desc

                            })
                        })
                    } else if (heading.indexOf("Education") != -1) {
                        lis = el.querySelectorAll(":scope > ul > li")
                        lis.forEach((li) => {
                            if (li.querySelector(":scope > i")) {
                                type = li.querySelector(":scope > i").innerText
                                strongs = li.querySelectorAll(":scope > strong")
                                if (strongs.length == 4) {
                                    degree = strongs[0].innerText
                                    specific = strongs[1].innerText
                                    university = strongs[2].innerText
                                    if (strongs[3]) {
                                        year = strongs[3].innerText
                                    } else {
                                        year = ""
                                    }

                                    education.push({
                                        type: type,
                                        degree: degree,
                                        specific: specific,
                                        university: university,
                                        year: year
                                    })
                                }
                            }
                        })
                    } else if (heading.indexOf("Projects") != -1) {
                        lis = el.querySelectorAll(":scope > ul > li > .tup")
                        lis.forEach((li) => {
                            projects.push(li.innerHTML)
                        })
                    }
                })
                return [key_skills, summary, workExp, education, projects, extra_info]
            })
            // console.log(await page2.$eval(".grntxt" , link => link.innerHTML))
            // sections = await page2.$eval('.section' , ele => ele.innerHTML );

            console.log(data)

            key_skills = data[0]
            summary = data[1]
            workExp = data[2]
            education = data[3]
            projects = data[4]
            extra_info = data[5]



            if (key_skills.length == 0 && summary.length == 0 && workExp.length == 0 && education.length == 0 && projects.length == 0) {
                console.log("all is empty something is wrong breaking out")
                console.log("current page: ", current_page, "index: ", i)
                break
            }
            extra_data["current_page"] = current_page
            extra_data["index"] = i
            res = await Candidate.updateOne({ "uname": uname }, {
                uname: uname,
                key_skills: key_skills,
                summary: summary,
                workExperiance: workExp,
                education: education,
                projects: projects,
                extra_data: extra_data,
                extra_info: extra_info
            }, { upsert: true });
            console.log("candidate inserted index", i, "page", current_page, "res", res)

            await page2.close()

        }
        console.log("clicking next")
        current_page++
        if (await page.$('a[title="Next"]') !== null) {
            try {
                await Promise.all([
                    page.click('a[title="Next"]'),
                    page.waitForNavigation()
                ])
            } catch (error) {
                console.log(error)
                return true
            }

            await get_page_data(browser, page, extra_data, start_page, start_page_index, current_page)
        } else {
            console.log("all completed!")
            return true
        }


    } else {
        console.log("all completed!")
        return true
    }
}

classification = [
    {
        "id": 99,
        "key": "software development", //IT
        "query": [
            { "name": "Software Developer", "ids": ["role99.01"], "search": ["software developer", "php developer", "web developer", "ui developer"] },
            { "name": "Graphic Designer", "ids": ["role99.09"] },
            { "name": "Team Lead Tech Lead", "ids": ["role99.02", "role99.04"] },
            { "name": "Database Architect", "ids": ["role99.05"] },
            { "name": "System Analyst", "ids": ["role99.03"] },
            { "name": "Technical Support", "ids": ["role99.15"] },
            { "name": "System Admin", "ids": ["role99.13"] },
            { "name": "Business Analyst", "ids": ["role99.21"] },
            { "name": "Technical Writer", "ids": ["role99.26", "role99.28", "role99.40"] },
            { "name": "Quality Assurance", "ids": ["role99.29", "role99.30"] },
            { "name": "Project Manager", "ids": ["role99.31"] },
            { "name": "Senior Management", "ids": ["role99.32", "role99.33", "role99.34", "role99.35"] },
            { "name": "Fresher Trainee", "ids": ["role99.37", "role99.38"] }
        ],
    },
    {
        "id": 1,
        "key": "accounts",
        "query": [
            { "name": "Chartered Accountant", "ids": ["role1.08"] },
            { "name": "Accounts Manager", "ids": ["role1.05"] },
            { "name": "Taxation", "ids": ["role1.03", "role1.04"] },
            { "name": "Accounts Executive Accountant", "ids": ["role1.01", "role1.07"] },
            { "name": "Financial Analyst", "ids": ["role1.13"] },
            { "name": "Financial Exec", "ids": ["role1.09", "role1.10"] },
            { "name": "Audit Manager", "ids": ["role1.14"] },
            { "name": "Company Secretary", "ids": ["role1.22"] },
            { "name": "Senior Management", "ids": ["role1.18", "role1.19", "role1.20", "role1.21"] },
            { "name": "Fresher Trainee", "ids": ["role1.24", "role1.25"] }
        ],
    },
    {
        "id": 12,
        "key": "HR Recruitment",
        "query": [
            { "name": "HR Executive", "ids": ["role12.01", "role12.03"] },
            { "name": "HR Manager", "ids": ["role12.02", "role12.04"] },
            { "name": "Admin", "ids": ["role12.09", "role12.10"] },
            { "name": "Head VP GM HR", "ids": ["role12.11", "role12.12", "role12.13", "role12.14", "role12.15"] },
            { "name": "Fresher Trainee", "ids": ["role12.17", "role12.18"] },
            { "name": "Payroll Executive", "ids": ["role12.21"] },
        ]
    },
    {
        "id": 22,
        "key": "Sales",
        "query": [
            { "name": "Sales Executive", "ids": ["role22.01", "role22.10", "role22.14", "role22.29"] },
            { "name": "Sales Business Development", "ids": ["role22.11", "role22.05", "role22.30"] },
            { "name": "Head VP GM HR", "ids": ["role22.23", "role22.44"] },
            { "name": "Fresher Trainee", "ids": ["role22.26", "role22.27"] },
        ]

    },
    {
        "id": 15,
        "key": "marketing",
        "query": [
            { "name": "Marketing Manager", "ids": ["role15.07", "role15.41", "role15.05", "role15.03", "role15.02"] },
            { "name": "Client Servicing", "ids": ["role15.08", "role15.09"] },
            { "name": "Events Exec", "ids": ["role15.14", "role15.15"] },
            { "name": "Digial Marketing", "ids": ["role15.46", "role15.47", "role15.52", "role15.56"] },
            { "name": "Trainee Fresher", "ids": ["role15.34", "role15.35"] },
            { "name": "Senior Management", "ids": ["role15.24", "role15.25", "role15.26", "role15.27", "role15.28"] }
        ]
    },
    {
        "id": 8,
        "key": "customer service",
        "query": [
            { "name": "Customer Care Executive", 'ids': ["role8.01", "role8.02"] },
            { "name": "Team Leader", 'ids': ["role8.03", "role8.04", "role8.10", "role8.11"] },
            { "name": "Senior Management", "ids": ["role8.28", "role8.29", "role8.30", "role8.31", "role8.32"] },
            { "name": "Trainee Fresher", "ids": ["role8.34", "role8.34"] },
        ]
    }, {
        "key": "legal",
        "id": 13,
        "query": [
        ]
    }, {
        "key": "Teaching Education",
        "id": 36,
        "query": [
            { "name": "Teachers", 'ids': ["role36.01", "role36.06","role36.03","role36.04","role36.05"] },
            { "name": "Language Teachers", 'ids': ["role36.25", "role36.26","role36.27","role36.28","role36.29"] },
            { "name": "Subject Teachers", 'ids': ["role36.39", "role36.40","role36.41","role36.42","role36.43"] },
            { "name": "Skill Teachers", 'ids': ["role36.51", "role36.52","role36.53","role36.54","role36.55"] },
            { "name": "University", 'ids': ["role36.02", "role36.59","role36.60","role36.61","role36.62"] },

        ]
    }]

//to search on indeed i think we should find the top designations we get from naukri and search them

async function parseByCustomClassification(nextIndustry = false) {
    const browser = await puppeteer.connect({ browserWSEndpoint: wsChromeEndpointurl });
    const page = await browser.newPage();
    console.log("connected to browser");

    await page.setUserAgent(userAgent.toString())

    await page.goto("https://freesearch.naukri.com/search/advSearch")



    progress = await NaukriProgress.findOne({ "type": "parseByCustomClassification" }).lean()


    if (progress) {


        classification_main_index = progress["classification_main_index"]
        classification_sub_index = progress["classification_sub_index"]

        if (nextIndustry) {
            console.log("next sub index!")
            classification_sub_index++

            if (classification_sub_index >= classification[classification_main_index]["query"].length) {
                console.log("next main index!", classification_sub_index)
                classification_sub_index = 0
                classification_main_index++

                if (classification_main_index >= classification.length) {
                    console.log("all finished")
                    process.exit(1)
                }
            }

            current_page = - 1
            page_index = -1
        } else {

            console.log("existing indexes main index", classification_main_index, "sub index", classification_sub_index)

            lastCandidate = await Candidate.findOne({
                "extra_data.type": "parseByCustomClassification",
                "extra_data.classification_main_index": classification_main_index,
                "extra_data.classification_sub_index": classification_sub_index,
                "extra_data.current_page": { $exists: true }
            })
                .sort({ "extra_data.current_page": -1 }).lean()

            // console.log(lastCandidate)
            if (lastCandidate) {
                current_page = lastCandidate["extra_data"]["current_page"]
                lastCandidate = await Candidate.findOne({
                    "extra_data.type": "parseByCustomClassification",
                    "extra_data.classification_main_index": classification_main_index,
                    "extra_data.classification_sub_index": classification_sub_index,
                    "extra_data.current_page": current_page
                })
                    .sort({ "extra_data.index": -1 }).lean()
                page_index = lastCandidate["extra_data"]["index"]
                console.log("previous current page ", current_page, " prev current index ", page_index)
            } else {
                current_page = - 1
                page_index = -1
            }
        }

    } else {
        classification_main_index = 0
        classification_sub_index = 0

        current_page = - 1
        page_index = -1


    }

    classification_main_id = classification[classification_main_index]["id"]
    classification_main_name = classification[classification_main_index]["key"]
    if (classification[classification_main_index]["query"].length > 0) {
        classification_sub_name = classification[classification_main_index]["query"][classification_sub_index]["name"]
        classification_sub_ids = classification[classification_main_index]["query"][classification_sub_index]["ids"]
    } else {
        classification_sub_name = ""
        classification_sub_ids = []
    }
    progress = {
        "type": "parseByCustomClassification",
        "classification_main_id": classification_main_id,
        "classification_main_name": classification_main_name,
        "classification_sub_name": classification_sub_name,
        "classification_sub_ids": classification_sub_ids,
        "classification_main_index": classification_main_index,
        "classification_sub_index": classification_sub_index
    }

    await NaukriProgress.update({ "type": "parseByCustomClassification" }, progress, { upsert: true })

    page.click('a[title="Remove all"]').catch((err) => { })

    console.log(classification_sub_ids, "sub ids")
    await page.evaluate((classification_main_id, classification_sub_ids) => {
        typeList = document.querySelector("#fareaList")
        lis = typeList.querySelectorAll(":scope li")
        lis.forEach((li) => {
            if (li.querySelector(":scope > input[type=checkbox]").getAttribute("value") == classification_main_id) {
                li.querySelector(":scope > input[type=checkbox]").click()
            }
        })
        classification_sub_ids.forEach((id) => {
            document.getElementById(id).click()
        })
    }, classification_main_id, classification_sub_ids)



    await Promise.all([
        page.click('input[value=TS]'),
        page.select('select[name=DAYSOLD]', '3650'),
        page.select('select[name=RES_PER_PAGE]', '160'),
    ])





    await Promise.all([
        page.click("#findResumes"),
        page.waitForNavigation({ waitUntil: 'networkidle0' })
    ])

    response = await get_page_data(browser, page, {
        "classification_main_id": classification_main_id,
        "classification_main_name": classification_main_name,
        "classification_sub_name": classification_sub_name,
        "classification_sub_ids": classification_sub_ids,
        "classification_main_index": classification_main_index,
        "classification_sub_index": classification_sub_index,
        "type": "parseByCustomClassification"
    }, current_page, page_index)

    if (response) {
        console.log("completed functional area ", classification_main_name)
    }
    await page.close()
    parseByCustomClassification(true)

}

parseByCustomClassification()

async function parseByFunctionalArea(nextIndustry = false) {
    const browser = await puppeteer.connect({ browserWSEndpoint: wsChromeEndpointurl });
    const page = await browser.newPage();
    console.log("connected to browser");

    await page.setUserAgent(userAgent.toString())

    await page.goto("https://freesearch.naukri.com/search/advSearch")



    progress = await NaukriProgress.findOne({ "type": "parseByFunctionalArea5" }).lean()


    if (progress) {
        functional_area_id = progress["functional_area_id"]

        if (nextIndustry) {
            console.log("starting new functional rea!")
            progress["functional_area_id"] = functional_area_id + 1
            current_page = - 1
            page_index = -1
        } else {

            console.log("existing functional area id", functional_area_id)

            lastCandidate = await Candidate.findOne({ "extra_data.type": "parseByFunctionalArea5", "extra_data.functional_area_id": functional_area_id, "extra_data.current_page": { $exists: true } }).sort({ "extra_data.current_page": -1 }).lean()
            // console.log(lastCandidate)
            if (lastCandidate) {
                current_page = lastCandidate["extra_data"]["current_page"]
                lastCandidate = await Candidate.findOne({ "extra_data.type": "parseByFunctionalArea5", "extra_data.functional_area_id": functional_area_id, "extra_data.current_page": current_page }).sort({ "extra_data.index": -1 }).lean()
                page_index = lastCandidate["extra_data"]["index"]
                console.log("previous current page ", current_page, " prev current index ", page_index)
            } else {
                current_page = - 1
                page_index = -1
            }
        }
    } else {
        functional_area_id = 1
        progress = {
            "type": "parseByFunctionalArea5",
            "functional_area_id": functional_area_id
        }
        current_page = - 1
        page_index = -1
    }

    await NaukriProgress.update({ "type": "parseByFunctionalArea5" }, progress, { upsert: true })

    let functional_areas = await page.evaluate((functional_area_id) => {
        functional_areas = []
        typeList = document.querySelector("#fareaList")
        lis = typeList.querySelectorAll(":scope li")
        lis.forEach((li) => {
            if (li.querySelector(":scope > input[type=checkbox]").getAttribute("value") == functional_area_id) {
                li.querySelector(":scope > input[type=checkbox]").click()
            }
            if (li.querySelector(":scope > .right").innerText !== "Any") {
                functional_areas.push({
                    "id": li.querySelector(":scope > input[type=checkbox]").getAttribute("value"),
                    "text": li.querySelector(":scope > .right").innerText
                })
            }
        })
        return functional_areas
    }, functional_area_id)

    does_industry_id_exists = true
    functional_area = ""
    functional_areas = functional_areas.sort((a, b) => {
        if (parseInt(a.id) === functional_area_id || parseInt(b.id) === functional_area_id) {
            functional_area = a.text
        }

        if (parseInt(a.id) > parseInt(b.id)) { return 1 } else { return -1 }
    })
    if (functional_area.length == 0) {
        console.log("indstry not existing skipping ", functional_area_id)
        await page.close()
        parseByFunctionalArea(true)
        console.log(functional_areas)
    } else {

        await Promise.all([
            page.click('input[value=TS]'),
            page.select('select[name=DAYSOLD]', '3650'),
            page.select('select[name=RES_PER_PAGE]', '160'),
        ])


        page.click('a[title="Remove all"]').catch((err) => { })


        await Promise.all([
            page.click("#findResumes"),
            page.waitForNavigation({ waitUntil: 'networkidle0' })
        ])

        response = await get_page_data(browser, page, {
            "functional_area_id": functional_area_id,
            "functional_area": functional_area,
            "type": "parseByFunctionalArea5"
        }, current_page, page_index)

        if (response) {
            console.log("completed functional area ", functional_area)
        }
        await page.close()
        parseByFunctionalArea(true)
    }

}

// parseByFunctionalArea()

async function parseByIndustryType(nextIndustry = false) {
    console.log("starting parse by industry")
    const browser = await puppeteer.connect({ browserWSEndpoint: wsChromeEndpointurl });
    const page = await browser.newPage();
    console.log("connected to browser");

    await page.setUserAgent(userAgent.toString())

    await page.goto("https://freesearch.naukri.com/search/advSearch")

    progress = await NaukriProgress.findOne({ "type": "parseByIndustryType" }).lean()

    if (progress && progress["type"]) {
        industry_id = progress["industry_id"]

        if (nextIndustry) {
            console.log("starting new industry!")
            progress["industry_id"] = industry_id + 1
            current_page = - 1
            page_index = -1
        } else {

            console.log("existing industry id", industry_id)

            lastCandidate = await Candidate.findOne({ "type": "parseByIndustryType", "extra_data.industry_id": industry_id, "extra_data.current_page": { $exists: true } }).sort({ "extra_data.current_page": -1 }).lean()
            // console.log(lastCandidate)
            if (lastCandidate) {
                current_page = lastCandidate["extra_data"]["current_page"]
                lastCandidate = await Candidate.findOne({ "type": "parseByIndustryType", "extra_data.industry_id": industry_id, "extra_data.current_page": current_page }).sort({ "extra_data.index": -1 }).lean()
                page_index = lastCandidate["extra_data"]["index"]
                console.log("previous current page ", current_page, " prev current index ", page_index)
            } else {
                current_page = - 1
                page_index = -1
            }
        }
    } else {
        industry_id = 2
        progress = {
            "type": "parseByIndustryType",
            "industry_id": industry_id
        }
        current_page = - 1
        page_index = -1
    }
    await NaukriProgress.update({ "type": "parseByIndustryType" }, progress, { upsert: true })

    let industries = await page.evaluate((industry_id) => {
        industries = []
        typeList = document.querySelector("#indTypeList")
        lis = typeList.querySelectorAll(":scope li")
        lis.forEach((li) => {
            if (li.querySelector(":scope > input[type=checkbox]").getAttribute("value") == industry_id) {
                li.querySelector(":scope > input[type=checkbox]").click()
            }
            if (li.querySelector(":scope > .right").innerText !== "Any") {
                industries.push({
                    "id": li.querySelector(":scope > input[type=checkbox]").getAttribute("value"),
                    "text": li.querySelector(":scope > .right").innerText
                })
            }
        })
        return industries
    }, industry_id)

    does_industry_id_exists = true
    industry_name = ""
    industries = industries.sort((a, b) => {
        if (parseInt(a.id) == industry_id)
            industry_name = a.text
        if (parseInt(a.id) > parseInt(b.id)) { return 1 } else { return -11 }
    })
    if (industry_name.length == 0) {
        console.log("indstry not existing skipping")
        await page.close()
        parseByIndustryType(true)
    } else {
        // console.log(industries)
        await Promise.all([
            page.click('input[value=TS]'),
            page.select('select[name=DAYSOLD]', '23'),
            page.select('select[name=RES_PER_PAGE]', '160'),
        ])


        page.click('a[title="Remove all"]').catch((err) => { })


        await Promise.all([
            page.click("#findResumes"),
            page.waitForNavigation({ waitUntil: 'networkidle0' })
        ])

        response = await get_page_data(browser, page, {
            "industry_id": industry_id,
            "industry_name": industry_name,
            "type": "parseByIndustryType"
        }, current_page, page_index)

        if (response) {
            console.log("completed industry ", industry_name)
        }
        await page.close()
        parseByIndustryType(true)
    }

}

// parseByIndustryType()

async function startParsing() {

    let res = await Candidate.updateMany({}, { "searchKey": "developer" })
    const browser = await puppeteer.connect({ browserWSEndpoint: wsChromeEndpointurl });
    const page = await browser.newPage();
    console.log("connected to browser");

    await page.setUserAgent(userAgent.toString())

    await page.goto("https://freesearch.naukri.com/search/advSearch")
    await Promise.all([
        page.waitFor('#ez_keyword_any'),
        page.$eval('#ez_keyword_any', el => el.value = 'developer'),
        page.click('input[value=TS]'),
        page.select('select[name=DAYSOLD]', '3650'),
        page.select('select[name=RES_PER_PAGE]', '160')
    ])

    await Promise.all([
        page.click("#findResumes"),
        page.waitForNavigation({ waitUntil: 'networkidle0' })
    ])

    console.log("next page opened")
    // sid=3746699201&LT=1577213671

    current_page = 0
    start_page = 9
    start_page_index = 17

    await get_page_data(browser, page, current_page, start_page, start_page_index)
}

// startParsing()