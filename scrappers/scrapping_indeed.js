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

let CompanyScheme = new Schema({}, { strict: false });
let CandidateScheme = new Schema({}, { strict: false });
let JobTitleScheme = new Schema({}, { strict: false });

let Company = mongoose.model('indeed_Company', CompanyScheme);
let Candidate = mongoose.model('indeed_Candidate', CandidateScheme);
let JobTitle = mongoose.model('indeed_JobTitle', JobTitleScheme);

var url = "mongodb://staging_recruit:staging_recruit@5.9.144.226:27017/staging_recruit";

mongoose.connect(url);

let db = mongoose.connection;

db.on('error', console.error.bind(console, 'MongoDB connection error:'));

query = ["developer"]
l = ["", "Delhi", "Mumbai%2C+Maharashtra", "Bangalore%2C+Karnataka", "Hyderabad%2C+Telangana", "Chennai%2C+Tamil+Nadu", "Pune%2C+Maharashtra"]


query_index = 0
location_index = 2
page_no = 6350

// const fetch = require('node-fetch')

// const getChromeWS = async () => {
//     let response = await fetch('http://127.0.0.1:9222/json/version')
//     console.log(response)
// }

// getChromeWS()

const wsChromeEndpointurl = 'ws://127.0.0.1:9222/devtools/browser/3a9b2370-68c8-4eea-a9f0-49c03e0f3ec0';

const sleep = (milliseconds) => {
    return new Promise(resolve => setTimeout(resolve, milliseconds))
}
async function startParsingCandidateQueryPage() {
    const browser = await puppeteer.connect({ browserWSEndpoint: wsChromeEndpointurl });
    const page = await browser.newPage();
    console.log("connected to browser");

    await page.setUserAgent(userAgent.toString())
    // try {
    //     await page.goto("https://secure.indeed.com/account/login")
    //     await page.waitFor('input[name=__email]');
    //     await page.$eval('input[name=__email]', el => el.value = 'excellenceseo@gmail.com');
    //     await page.$eval('input[name=__password]', el => el.value = 'java@123');
    //     await page.click("#login-submit-button")
    //     await page.waitForNavigation()
    // } catch (err) { console.error(err) }


    // function isLoginDone() {
    //     return new Promise((resolve, reject) => {
    //         max_check = 100
    //         count = 0
    //         console.log("checking if login is done")
    //         interval = setInterval(() => {
    //             if (count > max_check) {
    //                 console.log("quitting since you didn't put in 2fa")
    //                 reject()
    //             }
    //             if (page.url().indexOf("emailtwofactorauth") > 0) {
    //                 count++
    //                 console.log("its asking for 2fa")
    //                 console.log("waiting for you to put in manually! i am not fetching via imap for u.....")
    //                 resolve()
    //             } else {
    //                 clearInterval(interval)
    //             }
    //         }, 1000)
    //     })
    // }


    // isLoginDone().then(async () => {
    // await page.setRequestInterceptionEnabled(true);
    await page.goto('https://resumes.indeed.com/search?l=' + l[location_index] + '&lmd=all&q=' + query[query_index] + '&searchFields=&start=' + page_no);
    console.log("page opened");
    // await page.waitForNavigation({ waitUntil: 'networkidle0' })
    // console.log("network idle2 done");


    // await page.$eval('input[name=__email]', el => el.value = 'jobs@excellencetechnologies.in');
    // await sleep(10000)
    // await page.waitFor('input[name=__password]');
    // await page.$eval('input[name=__password]', el => el.value = 'Etech@123');
    // rezemp-ResumeSearchPage-results

    await page.setRequestInterception(true);
    page.on('request', interceptedRequest => {
        if (interceptedRequest.url().indexOf("botscore") > 0 || interceptedRequest.url().indexOf("rpc/log") > 0)
            interceptedRequest.abort();
        else
            interceptedRequest.continue();
    });

    page_wait_timeout = setTimeout(async () => {
        console.log("waited for 20sec but no response caome on page. so refresing")
        await page.reload()
        console.log("page reloaded")

    }, 20 * 1000)


    page.on('response', async response => {
        if (response.url().startsWith("https://resumes.indeed.com/rpc/search?")) {
            response.json().then((data) => {
                let totalJobResults = data.totalResultCount
                let refinements = data.refinements

                jobTitles = []
                companies = []

                if (refinements == null) {
                    console.log("its finished")
                    clearTimeout(page_wait_timeout)
                    page_no = 0
                    console.log("location index", location_index, " location ", l[location_index])
                    console.log("query index", query_index, ' query ', query[query_index])
                    if (location_index == l.length - 1) {
                        if (query_index == query.length - 1) {
                            console.log("fully finished now ")
                        } else {
                            query_index++
                            location_index = 0
                            startParsingCandidateQueryPage()
                        }
                    } else {
                        location_index++
                        startParsingCandidateQueryPage()
                    }
                } else {
                    // refinements.forEach((ele) => {
                    //     if (ele["id"] == "jtid") {
                    //         jobTitles = ele["options"]
                    //         jobTitles.forEach(async (row) => {
                    //             await JobTitle.update({ "id": row.id }, row, { upsert: true })
                    //         })
                    //     }
                    //     if (ele["id"] == "cmpid") {
                    //         companies = ele["options"]
                    //         companies.forEach(async (row) => {
                    //             await Company.update({ "id": row.id }, row, { upsert: true })
                    //         })
                    //     }
                    // })
                }
            })
        }
        if (response.url().startsWith("https://resumes.indeed.com/rpc/resume")) {
            console.log(response.url())
            //   console.log("response code: ", response.status());
            response.json().then(async (data) => {
                // for(var attributename in data){
                //     console.log(attributename+": "+data[attributename]);
                // }
                // console.log(data.length)

                data["resumeModels"].forEach(async (row) => {
                    res = await Candidate.update({ "accountKey": row.accountKey }, row, { upsert: true });
                    console.log("candidate inserted", res)
                })
                console.log("waiting for next page")
                await page.waitFor(".rezemp-pagination-nextbutton")
                await page.click(".rezemp-pagination-nextbutton")

                console.log("clicked next page and cleared timeout")

                clearTimeout(page_wait_timeout)

                page_wait_timeout = setTimeout(async () => {
                    console.log("waited for 20sec but no response caome on page. so refresing")
                    await page.reload()
                    console.log("page reloaded")

                }, 20 * 1000)
            })
        }
        // do something here
    });
    // })







    // await page.screenshot({ path: 'example0.png', fullPage: true });
    // await page.pdf({path: 'hn.pdf', format: 'A4'});
    // await page.click('button[type=submit]');
    // await page.screenshot({ path: 'example1.png' });
    // await page.click('.jobTab')
    // await page.waitForNavigation({ waitUntil: 'networkidle0' })
    // await page.screenshot({ path: 'example2.png' });
    //   console.log('Dimensions:', dimensions);
    // await browser.close();
}

// startParsingCandidateQueryPage()


async function startParsingDetailPage() {

    try {


        const browser = await puppeteer.connect({ browserWSEndpoint: wsChromeEndpointurl });
        const page = await browser.newPage();
        console.log("connected to browser");

        await page.setUserAgent(userAgent.toString())

        candidateData = await Candidate.findOne({
            "full_checked": { "$exists": false }
            // "accountKey" : "7ded4f80abab0479"
        }).limit(1).lean()

        console.log("candidate found", candidateData.accountKey)

        candidateData["full_checked"] = true

        count = await Candidate.countDocuments({
            "accountKey": candidateData.accountKey
        })

        if (count > 1) {
            console.log("more than one candidate? ", count)
            res = await Candidate.deleteMany({
                "accountKey": candidateData.accountKey,
                "_id": {
                    "$ne": candidateData._id
                }
            })
            console.log("candidate deleted ", res)
        }

        candidateStringfy = JSON.stringify(candidateData)

        if (candidateStringfy.indexOf("...") == 0) {
            console.log("no needed ")
            candidateData["full_parse_needed"] = false
        } else {
            candidateData["full_parse_needed"] = true


            // console.log(candidateData)

            await page.goto('https://resumes.indeed.com/resume/' + candidateData.accountKey);

            // console.log("network idle2 done");


            // await page.$eval('input[name=__email]', el => el.value = 'jobs@excellencetechnologies.in');
            // await sleep(10000)
            // await page.waitFor('#res_summary');
            // await page.waitForNavigation()

            console.log("page opened");
            // await page.$eval('input[name=__password]', el => el.value = 'Etech@123');
            // rezemp-ResumeSearchPage-results

            page_wait_timeout = setTimeout(async () => {
                console.log("waited for 20sec but no response caome on page. so refresing")
                await page.reload()
                console.log("page reloaded")

            }, 20 * 1000)

            await page.setRequestInterception(true);
            page.on('request', interceptedRequest => {
                if (interceptedRequest.url().indexOf("botscore") > 0 || interceptedRequest.url().indexOf("rpc/log") > 0)
                    interceptedRequest.abort();
                else
                    interceptedRequest.continue();
            })

            // let res_summary = await page.$eval("#res_summary" , link => link.innerText)
            // console.log(res_summary)

            data = await page.evaluate(() => {
                res_summary = document.querySelector("#res_summary")
                if (res_summary) {
                    res_summary = res_summary.innerText
                } else {
                    res_summary = ""
                }

                workExpDetails = []

                workExpDiv = document.querySelector('.workExperience-content')
                if (workExpDiv) {
                    workExpItems = workExpDiv.querySelectorAll(":scope > .items-container > .work-experience-section")
                    workExpItems.forEach((item) => {
                        id = item.getAttribute("id")
                        desc = item.querySelector(":scope > .data_display > .work_description")
                        if (desc) {
                            desc = desc.innerText
                        } else {
                            desc = ""
                        }
                        workExpDetails.push({
                            id: id.replace("workExperience-", ""),
                            desc: desc
                        })
                    })
                }

                skills = []
                skillDiv = document.querySelector('#skills-items')
                if (skillDiv) {
                    skillsSpan = skillDiv.querySelectorAll(":scope > .data_display > .skill-container > .skill-text")

                    skillsSpan.forEach((el) => {
                        skills.push(el.innerText)
                    })

                }




                additionalItem = ""

                addDiv = document.querySelector("#additionalinfo-section")
                if (addDiv)
                    additionalItem = addDiv.querySelector(":scope > .data_display > div").innerText

                return [res_summary, workExpDetails, skills, additionalItem]
            })

            if (data[0].length == 0 && data[1].length == 0 && data[2].length == 0 && data[3].length == 0) {
                console.log("all is empty something is wrong breaking out")
                process.exit()
            }

            clearTimeout(page_wait_timeout)

            console.log(data)

            if (data[0].length > 0)
                candidateData["summary"] = data[0]

            if (data[3].length > 0)
                candidateData["additionalInformation"] = data[3]

            workExperience = candidateData.workExperience

            // console.log(candidateData)
            workExperience2 = []
            workExperience.forEach((item) => {
                data[1].forEach((d) => {
                    if (d["id"] == item["id"]) {
                        item["description"] = d["desc"]
                    }
                })

                workExperience2.push(item)
            })
            candidateData.workExperience = workExperience2

            candidateData["skills_full_data"] = data[2]

            await page.close()

        }
        res = await Candidate.updateOne({
            "accountKey": candidateData.accountKey
        }, candidateData)

        console.log(res)

        console.log("candidate updated", candidateData.accountKey)

    } catch (error) {
        console.error(error)
        // await page.reload()
        // console.log("page reloaded")
        process.exit() //pm2 will restart it 
    }

    startParsingDetailPage()

}



startParsingDetailPage()


async function checkCandidateDetailPage() {

    candidateDatas = await Candidate.find({
        "full_checked": { "$exists": false }
        // "accountKey" : "7ded4f80abab0479"
    }).lean()

    for (i = 0; i < candidateDatas.length; i++) {
        candidateData = candidateDatas[i]
        console.log("candidate data", i)
        count = await Candidate.countDocuments({
            "accountKey": candidateData.accountKey
        })

        if (count > 1) {
            console.log("more than one candidate? ", count)
            res = await Candidate.deleteMany({
                "accountKey": candidateData.accountKey,
                "_id": {
                    "$ne": candidateData._id
                }
            })
            console.log("candidate deleted ", res)
        }

        candidateStringfy = JSON.stringify(candidateData)

        if (candidateStringfy.indexOf("...") == 0) {
            console.log("no needed ")
            // candidateData["full_parse_needed"] = false
        } else {
            // candidateData["full_parse_needed"] = true
        }
    }
    
}
