# -*- coding: utf-8 -*-
import ast
from collections import defaultdict
import datetime
from forex_python import converter
from functools import lru_cache
import random
from tempfile import NamedTemporaryFile
from time import sleep
import regex
import requests
from lxml import etree, html

# employer size
ES_ANY = 0
ES_0_200 = 1
ES_201_500 = 2
ES_501_1000 = 3
ES_1001_5000 = 4
ES_5001_PLUS = 5

__all__ = ["Search", "Throttler", "ProgressTracker", "ScrapeError", "TerminalScrapeError", "ES_ANY", "ES_0_200",
           "ES_201_500", "ES_501_1000", "ES_1001_5000", "ES_5001_PLUS"]


class Throttler:
    # provides throttle(), which injects delays between calls to maintain a minimum average call rate
    # it uses an exponential distribution (which models the duration between poisson events)
    # and a minimum delay (to loosely model how quickly a human would be able to click a link)
    # all durations are in seconds
    def __init__(self, average_rate=1.5, minimum_delay=0.673):
        # a lower average rate sometimes gave me bot warnings
        self.next_allowed_run = datetime.datetime.utcnow()
        self.average_rate = average_rate
        self.minimum_delay = minimum_delay

    def _generate_next_delay(self):
        return self.minimum_delay + random.expovariate(1.0 / (self.average_rate - self.minimum_delay))

    def throttle(self, func):
        if self.next_allowed_run > datetime.datetime.utcnow():
            sleep((self.next_allowed_run - datetime.datetime.utcnow()).total_seconds())
        self.next_allowed_run = datetime.datetime.utcnow() + datetime.timedelta(seconds=self._generate_next_delay())
        return func()


class ProgressTracker:
    """
    A multi-level, strictly hierarchical progress tracker.
    "Processing location 1/2, keyword 2/4, industry 5/13, page 12, job 28/30"
    """
    def __init__(self, order=None, autoprint=True, autoprint_granularity=None):
        self.order = order or []
        self.current = defaultdict(int)
        self.total = {}
        self.autoprint = autoprint
        self.autoprint_granularity = autoprint_granularity

    def set_total(self, name, total):
        self.register_name(name)
        self.total[name] = total

    def set_current(self, name, total):
        self.register_name(name)
        self.current[name] = total

    def increment(self, name, by=1):
        self.register_name(name)
        self.current[name] += by
        self.decrement_later(name)
        if self.autoprint:
            self.handle_autoprint(name)

    def decrement_later(self, name):
        for n in self.order[self.order.index(name)+1:]:
            self.current[n] = 0
            self.total.pop(n, None)

    def handle_autoprint(self, name):
        granularity = self.autoprint_granularity or self.order[-1]
        if name == granularity:
            print(self.render(granularity))

    # takewhile, except it returns the first failing value as well
    @staticmethod
    def takewhileinc(predicate, iterable):
        for x in iterable:
            if not predicate(x):
                yield x
                break
            yield x

    # dropwhile, except it returns the first passing value as well
    @staticmethod
    def dropwhileinc(predicate, iterable):
        for x in iterable:
            if predicate(x):
                yield x
                break
            yield x

    def render(self, granularity=None):
        components = []
        for name in self.order:
            trivial = name in self.total and self.current[name] == 1 and self.total[name] == 1
            if not trivial:  # don't render 1/1, basically
                components.append(self._render_name(name))
            if name == granularity:
                # and don't render anything below the requested granularity
                break
        return "Processing " + ", ".join(components)

    def register_name(self, name):
        if name not in self.order:
            self.order.append(name)

    def _render_name(self, name):
        total = self.total.get(name)
        current = self.current[name]
        if total:
            return "%s %s/%s" % (name, current, total)
        return "%s %s" % (name, current)


throttler = Throttler()  # this is global, because multiple different searches need to all obey the same rate limit


class ScrapeError(Exception):
    pass


class TerminalScrapeError(ScrapeError):
    pass


class TransientScrapeError(ScrapeError):
    pass


class BaseSearch:
    def __init__(self, minimum_salary, minimum_rating, industry_code,
                 minimum_employer_size, paranoid, throttler_, progress_tracker):
        self.minimum_salary = minimum_salary
        self.minimum_rating = minimum_rating
        self.industry_code = industry_code
        self.minimum_employer_size = minimum_employer_size
        self.paranoid = paranoid
        self.throttler = throttler_
        self.progress = progress_tracker
        self.session = requests.Session()
        self.session.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'www.glassdoor.com',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        }

    def get_home_page(self):
        # retrieve the home page to simulate ourselves being a "real user"
        response = self.get("https://www.glassdoor.com/")
        self.session.headers['Referer'] = response.url

    def post(self, *args, **kwargs):
        return self.requests_op(self.session.post, *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.requests_op(self.session.get, *args, **kwargs)

    # wrapper around requests operations, to make sure we obey the throttle
    def requests_op(self, op, *args, **kwargs):
        retries = 0
        while True:
            try:
                response = self.throttler.throttle(lambda: op(*args, **kwargs))
                self.check_page_for_errors(response)
                return response
            except (TransientScrapeError, requests.RequestException) as e:
                print(e)
                sleep(1*2**retries)
                retries += 1
                if retries > 12:  # up to 4096, ~68 minutes
                    print("Out of retries, failing")
                    raise
                continue

    @staticmethod
    def check_page_for_errors(response):
        # checks if the page is an error page, parses the error message, and re-raises Terminal or Transient
        is_potential_bot_match = regex.search(r'isPotentialBot":(true|false)', response.text)
        is_potential_bot = is_potential_bot_match and is_potential_bot_match.groups()[0] == "true"
        suspicious_activity = bool(regex.search(r'We have been receiving some suspicious activity from you or '
                                                r'someone sharing your internet network.', response.text))
        gateway_timeout = regex.search(r'The web server reported a gateway time-out error.', response.text)
        bad_gateway = regex.search(r'The web server reported a bad gateway error.', response.text)
        volume_timeout = regex.search(r'your search timed out due to high volumes', response.text)
        if is_potential_bot or suspicious_activity:
            raise TerminalScrapeError("Glassdoor suspects us of being a bot while getting %s (is_potential_bot: %s, 'suspicious activity': %s)!" % (response.url, is_potential_bot, suspicious_activity))
        elif gateway_timeout:
            raise TransientScrapeError("Gateway timeout")
        elif bad_gateway:
            raise TransientScrapeError("Bad gateway")
        elif volume_timeout:
            # I'm not actually sure if this means our request volume, or general request volume across the site
            # regardless, a retry usually makes this go away
            raise TransientScrapeError("Volume timeout")
        else:
            return True


class Search(BaseSearch):
    # this class encapsulates the query parameters, requests session, and search progress tracking
    def __init__(self, keywords, locations, minimum_salary=None, minimum_rating=None, industry_code=-1,
                 minimum_employer_size=ES_ANY, paranoid=False, throttler_=None, progress_tracker=None):
        self.keywords = [keywords] if isinstance(keywords, str) else keywords
        self.locations = [locations] if isinstance(locations, str) else locations
        super().__init__(minimum_salary, minimum_rating, industry_code, minimum_employer_size, paranoid,
                         throttler_ or throttler, progress_tracker or ProgressTracker())

    def run(self):
        if self.paranoid:
            self.get_home_page()
        results = dict()
        self.progress.set_total("location", len(self.locations))
        for location in self.locations:
            self.progress.increment("location")
            self.progress.set_total("keyword", len(self.keywords))
            for keyword in self.keywords:
                self.progress.increment("keyword")
                # assume single industry; if we fork into multiple industries, that code will overwrite this
                self.progress.set_total("industry", 1)
                self.progress.set_current("industry", 1)
                for listing in SingleSearch(keyword, location, self.minimum_salary, self.minimum_rating,
                                            self.industry_code, self.minimum_employer_size, self.paranoid,
                                            self.throttler, self.progress).run():
                    results[listing['listing_id']] = listing
        return list(results.values())


class SingleSearch(BaseSearch):
    def __init__(self, keyword, location, minimum_salary, minimum_rating, industry_code,
                 minimum_employer_size, paranoid, throttler_, progress_tracker):
        self.keyword = keyword
        self.location_string = location
        self.location_compound_id = None
        super().__init__(minimum_salary, minimum_rating, industry_code, minimum_employer_size, paranoid,
                         throttler_, progress_tracker)

    def run(self):
        data = self.figure_out_query_params()
        result = []
        page_number = 1
        current_url = "https://www.glassdoor.com/Job/jobs.htm"
        response = self.post(current_url, data=data)

        self.session.headers['Referer'] = response.url
        parser = html.fromstring(response.text)
        promised_jobs = self.parse_promised_jobs(parser)
        if promised_jobs > 900 and self.industry_code == -1:
            # Glassdoor caps searches to 30 pages, which is around 900 jobs (most pages contain 30 jobs)
            # We use a workaround: we split up the search into multiple searches, one per industry code
            # We know every industry code, and they are all mutually exclusive, so this is guaranteed to partition the
            # search space without omissions or duplicates
            # That said, the new searches aren't guaranteed to be below 900 themselves
            overall_result = []
            industries = list(filter(lambda t: t[0] != '-1', self.parse_industry_options(parser).items()))
            self.progress.set_total("industry", len(industries))
            self.progress.set_current("industry", 0)
            for index, (industry_code, industry_name) in enumerate(industries):
                self.progress.increment("industry")
                overall_result += SingleSearch(self.keyword, self.location_string, self.minimum_salary,
                                               self.minimum_rating, industry_code, self.minimum_employer_size,
                                               self.paranoid, self.throttler, self.progress).run()
            return overall_result
        self.progress.register_name("page")
        while True:
            self.progress.increment("page")
            parser = html.fromstring(response.text)
            base_url = "https://www.glassdoor.com"
            parser.make_links_absolute(base_url)
            new_promised_jobs = self.parse_promised_jobs(parser)

            this_page_listings = self.listings_from_page(parser, response.url)
            result += this_page_listings
            if new_promised_jobs != promised_jobs:
                if abs(new_promised_jobs - promised_jobs) > 10:
                    # I have no idea why this happens, but sometimes the query messes up mid-pagination and
                    # wildly changes your result set; a re-query fixes it
                    print("Large promised jobs jump, retrying the query")
                    # TODO this messes up the progress, but we don't know how much to rewind it by
                    # maybe add a checkpointing function? christ it's getting complex for some goddamn progress tracking
                    # TODO maybe add RetryJob, RetryPage, RetryIndustry exceptions?
                    return SingleSearch(self.keyword, self.location_string, self.minimum_salary, self.minimum_rating,
                                        self.industry_code, self.minimum_employer_size, self.paranoid, self.throttler,
                                        self.progress).run()
                promised_jobs = new_promised_jobs
            if not this_page_listings:
                self.fail_dumping_response("Got an unknown page with no listings", response)

            next_page = parser.xpath('//li[@class="next"]//a/@href')
            if not next_page:
                break
            current_url = next_page[0]
            response = self.get(current_url)
            self.session.headers['Referer'] = response.url
            if self.not_found(response):
                # artificial 30 page limit has hit us
                print("Glassdoor artificial 30 page truncation!")
                break
            page_number += 1
        return result

    def figure_out_query_params(self):
        # retrieve the location code from the location string
        location_params = {"term": self.location_string, "maxLocationsToReturn": 1}
        location_response = self.post("https://www.glassdoor.com/findPopularLocationAjax.htm?",
                                      data=location_params).json()[0]
        self.location_compound_id = (location_response['locationType'], int(location_response['locationId']))
        data = {
            "clickSource": "searchBtn",
            "jobType": "",
            "locId": self.location_compound_id[1],
            "locT": "C",
            "sc.keyword": self.keyword,
            "suggestChosen": "false",
            "suggestCount": 0,
            "typedKeyword": self.keyword,
        }

        if self.paranoid:
            # do an initial post to "get to the options bar"; this isn't necessary,
            # but a real user wouldn't be able to send all the right kwargs without doing this post first
            response = self.post("https://www.glassdoor.com/Job/jobs.htm", data=data)
            self.session.headers['Referer'] = response.url

        # now add in all the stuff you weren't supposed to be able to add initially
        data.update({
            "jobType": "fulltime",
            "employerSizes": str(self.minimum_employer_size),
            "industryId": str(self.industry_code),
            "cityId": "-1",
            "companyId": "-1",
            "fromAge": "-1",
            "radius": "-1",
            # "gdToken" ??  # regex.search(r'gdToken":"([^"]+)"',parser.text_content()).groups()[0]
            # TODO no idea what ^^this is, but its propagation is non-trivial, and the queries seem to work without it
        })
        if self.minimum_rating is not None:
            data.update({"minRating": str(float(self.minimum_rating))})

        # remove all the search-click-related fields
        for k in ["typedKeyword", "suggestChosen", "suggestCount", "clickSource"]:
            data.pop(k)
        if self.minimum_salary is not None:
            # do a post with all the non-salary options
            # this isn't a paranoia thing; this is the only way to know whether our location supports salary filtering
            response = self.post("https://www.glassdoor.com/Job/jobs.htm", data=data)
            self.session.headers['Referer'] = response.url
            salary_options = self.parse_salary_options(html.fromstring(response.text))
            # now finally add salary, if possible
            if not salary_options:
                # salary options not available for this search (probably location based)
                print("Warning: salary filtering not available for this search, proceeding without")
            else:
                data.update({
                    "minSalary": str(self.nearest(self.minimum_salary, salary_options)),
                    "includeNoSalaryJobs": "false",
                })
        return data

    @staticmethod
    def nearest(target, options):
        return min(options, key=lambda x: abs(target - x))

    @staticmethod
    def not_found(response):
        return bool(regex.search(r"Sorry, we can't find that page", response.text))

    @staticmethod
    def extract(parser, xpath, type_=str):
        parse = parser.xpath(xpath)
        if parse is None:
            return None
        items = list(map(lambda x: x.strip(" –\n\r,"), parse))
        if not items:
            return None
        return type_(items[0])

    @staticmethod
    def parse_location(s):
        state_parts = list(map(str.strip, regex.findall(",\s?(.*)\s?", s)))
        state = state_parts[0] if state_parts else None
        city = s.replace(", %s" % state, '').strip()
        return city, state

    @classmethod
    def parse_salary(cls, parser):
        salary_string = parser.xpath('.//span[@class="green small"]/text()')
        if not salary_string:
            return None
        return tuple(map(cls.parse_salary_definition, salary_string[0].strip().split("-")))

    def listings_from_page(self, parser, url):
        result = []
        jobs = parser.xpath('//li[@class="jl"]')
        self.progress.set_total("job", len(jobs))
        for job_index, job in enumerate(jobs):
            self.progress.increment("job")
            city, state = self.parse_location(self.extract(job, './/span[@class="subtle loc"]/text()'))
            listing_url = self.extract(job, './/a/@href')
            listing = {
                "title": self.extract(job, './/a/text()'),
                "company": self.extract(job, './/div[@class="flexbox empLoc"]/div/text()'),
                "location": self.extract(job, './/span[@class="subtle loc"]/text()'),
                "requested_location": self.location_string,
                "city": city,
                "state": state,
                "rating": self.extract(job, './/span[@class="compactStars "]/text()', float),
                "url": listing_url,
                "listing_id": self.parse_listing_id(listing_url),
            }
            details_page_parser = self.get_details_page(listing_url)
            salary_range = self.parse_salary(job) or self.get_salary_the_hard_way(listing["title"], details_page_parser)
            if salary_range:
                if isinstance(salary_range[0], (tuple, list)) or isinstance(salary_range[1], (tuple, list)):
                    raise Exception(salary_range)
                if (salary_range[0] + salary_range[1]) / 2 < 100:
                    self.fail_dumping_text_url("Scraped an unreasonably small salary", parser.text_content(), url)
                listing["salary"] = salary_range
            listing["description"] = self.parse_description(details_page_parser)
            result.append(listing)
        return result

    def get_details_page(self, listing_url):
        details_url = regex.sub(r'partner/jobListing.htm\?', 'job-listing/details.htm?', listing_url)
        details_page_response = self.get(details_url)
        details_page_parser = html.fromstring(details_page_response.text)
        details_page_parser.make_links_absolute(details_url)
        return details_page_parser

    @staticmethod
    def parse_description(details_page_parser):
        description = details_page_parser.xpath('//div[contains(@class, "jobDescriptionContent")]')
        if not description:
            return ""
        return "\n".join(etree.XPath(".//text()")(description[0]))

    def get_salary_the_hard_way(self, job_title, details_page_parser):
        # look up all salaries of the company by job title and location; sometimes it's listed there
        # get to the salaries link by mangling the photos link in the details page
        photo_links = details_page_parser.xpath('//*[contains(@href, "Photos")]/@href')
        photos_link = next(filter(lambda l: "Office-Photos-IMG" not in l, photo_links))
        salary_url = regex.sub(r'Photos', 'Salary', regex.sub(r'Office-Photos-', 'Salaries-', photos_link))
        params = {"selectedLocationString": "%s,%s" % (self.location_compound_id[0],
                                                       self.location_compound_id[1]),
                  "filter.jobTitleFTS": job_title,
                  "sort.ascending": "false",
                  "sort.sortType": "MC"}
        response = self.get(salary_url, params=params)
        parser = html.fromstring(response.text)
        salaries = parser.xpath('//div[contains(@class, "salaryList")]//div[contains(@class, "SalaryRowStyle__row")]')
        sals = []
        for salary_parser in salaries:
            salary_job_title = salary_parser.xpath('.//div[contains(@class,"JobInfoStyle__jobTitle")]/a/text()')[0]
            # TODO use this to estimate confidence
            sample_size = int(salary_parser.xpath('.//div[contains(@class,"JobInfoStyle__jobCount")]/text()')[0])
            salary_range = tuple(map(self.parse_salary_definition,
                                     salary_parser.xpath('.//div[contains(@class,"RangeBarStyle__values")]/span/text()')))
            sals.append((salary_job_title, sample_size, salary_range))
            if salary_job_title == job_title:
                return salary_range
        return None

    @classmethod
    def fail_dumping_response(cls, reason, response):
        cls.fail_dumping_text_url(reason, response.text, response.url)

    @classmethod
    def fail_dumping_text_url(cls, reason, text, url):
        cls.dump_text_url(text, url)
        raise TerminalScrapeError(reason)

    @classmethod
    def dump_response(cls, response):
        cls.dump_text_url(response.text, response.url)

    @staticmethod
    def dump_text_url(response_text, url):
        file = NamedTemporaryFile(mode='w', delete=False)
        print("Wrote out response to %s; original url was %s" % (file.name, url))
        file.write(response_text)

    @staticmethod
    def parse_listing_id(url):
        return regex.search(r'jobListingId=([^&]+)', url).groups()[0]

    @staticmethod
    def parse_promised_jobs(parser):
        # parse the total amount of jobs glassdoor claims our search to contain
        # for some reason this amount is given in two different formats sometimes
        try:
            j1 = parser.xpath('//*[@class="jobsCount"]/text()')
            j2 = regex.search(r'([0-9,]+)', j1[0]).groups()[0]
            j3 = regex.sub(r',', '', j2)
            return int(j3)
        except IndexError:
            try:
                j1 = parser.xpath('//h1[@id="jobTitle"]/text()')[0]
                return int(regex.search("We found ([0-9]+)", j1).groups()[0])
            except IndexError:
                return None

    @staticmethod
    def parse_gd_token(parser):
        return regex.search(r'gdToken":"([^"]+)"', parser.text_content()).groups()[0]

    get_rate = lru_cache()(converter.get_rate)

    @classmethod
    def parse_salary_definition(cls, salary):
        per_interval = regex.search(r'per (hour)', salary)
        per_multipliers = {"hour": 8*(365.25*5/7)}
        per_multiplier = per_multipliers[per_interval.groups()[0]] if per_interval else 1
        currencies = ["$", "CHF"]
        multipliers = {"m": 1000000, "k": 1000, "": 1}
        currencies_regex = "(%s)" % "|".join(map(regex.escape, currencies))
        multipliers_regex = "(%s)" % "|".join(map(regex.escape, multipliers.keys()))
        currency, amount, multiplier = regex.findall(r'%s([0-9]+)%s' % (currencies_regex, multipliers_regex),
                                                     salary,
                                                     flags=regex.IGNORECASE)[0]
        currency_multiplier = cls.get_rate(currency, 'USD') if currency != '$' else 1
        result = int(amount) * multipliers[multiplier.lower()] * per_multiplier * currency_multiplier
        return result

    @classmethod
    def parse_industry_options(cls, parser):
        return cls.parse_filter_options(parser, "INDUSTRY")

    @classmethod
    def parse_salary_options(cls, parser):
        return list(map(int, cls.parse_filter_options(parser, "SALRANGE").keys()))

    @staticmethod
    def parse_filter_options(parser, option):
        t = list(filter(lambda s: '"filterOptions":"' in s.text_content(), parser.xpath("//script")))[0].text_content()
        return ast.literal_eval(regex.sub(r'\\(.)',
                                          lambda x: x.groups()[0],
                                          regex.search(r'%s.*?\\"options\\":({.*?})' % option, t).groups()[0]))
