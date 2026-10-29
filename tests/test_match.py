"""One test per branch in match.decide, each named after the mistake it prevents."""

import unittest

from champion import companies
from champion.match import HOLD, MATCH, NO_MATCH, Champion, Signal, decide, decide_case, run

CH = Champion("c1", "Robert Chen", "Northwind Travel", "VP Finance", "Austin",
              "https://linkedin.example/in/robert-chen", "2026-03-10")


def sig(**kw) -> Signal:
    base = dict(id="s1", name="Robert Chen", company="Fabrikam", title="CFO", city="Austin",
                profile=None, started="2026-05", history=("Northwind Travel",))
    return Signal(**{**base, **kw})


class Decide(unittest.TestCase):
    def test_same_profile_url_is_proof_even_with_a_nickname(self):
        d = decide(CH, sig(name="Bob Chen", profile="https://www.linkedin.example/in/robert-chen/", history=None))
        self.assertEqual(d.decision, MATCH)
        self.assertEqual((d.proof, d.anchor), ("same profile URL as the CRM record", "profile"))

    def test_promotion_at_the_same_company_is_not_a_move(self):
        d = decide(CH, sig(company="Northwind Travel Inc."))
        self.assertEqual(d.decision, NO_MATCH)
        self.assertIn("not a move", d.reasons[0])

    def test_renamed_company_is_still_the_same_company(self):
        groups = companies.alias_groups([("Northwind Travel", "Northwind")])
        self.assertEqual(decide(CH, sig(company="Northwind"), groups).decision, NO_MATCH)

    def test_same_profile_new_surname_and_old_company_in_history_is_a_match(self):
        d = decide(CH, sig(name="Robert Lee", profile=CH.profile))
        self.assertEqual(d.decision, MATCH)
        self.assertIn("Northwind Travel in their history", d.proof)

    def test_same_profile_but_dates_say_they_may_not_have_left_is_held(self):
        d = decide(CH, sig(profile=CH.profile, started="2025-06"))
        self.assertEqual(d.decision, HOLD)
        self.assertIn("may not have left", d.reasons[0])

    def test_same_profile_with_a_short_form_first_name_is_a_match(self):
        ch = Champion("c9", "Oluwaseun Adeyemi", "Northwind Travel", profile="https://linkedin.example/in/seun-a")
        d = decide(ch, sig(name="Seun Adeyemi", profile="https://linkedin.example/in/seun-a"))
        self.assertEqual((d.decision, d.anchor), (MATCH, "profile"))

    def test_short_form_without_profile_is_held(self):
        ch = Champion("c9", "Oluwaseun Adeyemi", "Northwind Travel", city="Austin")
        self.assertEqual(decide(ch, sig(name="Seun Adeyemi")).decision, HOLD)

    def test_same_profile_new_surname_without_history_is_held(self):
        self.assertEqual(decide(CH, sig(name="Robert Lee", profile=CH.profile, history=None)).decision, HOLD)

    def test_same_profile_different_first_name_is_held(self):
        self.assertEqual(decide(CH, sig(name="Noor Haddad", profile=CH.profile)).decision, HOLD)

    def test_new_surname_with_old_company_is_held_not_dropped(self):
        self.assertEqual(decide(CH, sig(name="Robert Lee")).decision, HOLD)

    def test_different_name_is_dropped(self):
        self.assertEqual(decide(CH, sig(name="Siobhan Walsh")).decision, NO_MATCH)

    def test_different_profile_with_shared_history_is_held(self):
        d = decide(CH, sig(profile="https://linkedin.example/in/rchen-2"))
        self.assertEqual(d.decision, HOLD)
        self.assertIn("profile URL differs", d.reasons[0])

    def test_profile_url_formats_are_the_same_profile(self):
        for url in ("http://in.linkedin.example/in/robert-chen?trk=x", "https://www.linkedin.example/in/Robert-Chen/"):
            with self.subTest(url):
                self.assertEqual(decide(CH, sig(profile=url, history=None)).decision, MATCH)

    def test_different_profile_and_no_history_is_held_not_dropped(self):
        d = decide(CH, sig(profile="https://linkedin.example/in/rchen-2", history=None))
        self.assertEqual(d.decision, HOLD)

    def test_different_profile_without_shared_history_is_a_namesake(self):
        d = decide(CH, sig(profile="https://linkedin.example/in/rchen-2", history=("Contoso",)))
        self.assertEqual(d.decision, NO_MATCH)

    def test_no_history_is_held(self):
        self.assertEqual(decide(CH, sig(history=None)).decision, HOLD)
        self.assertEqual(decide(CH, sig(history=())).decision, HOLD)

    def test_no_history_and_started_before_last_seen_is_dropped(self):
        d = decide(CH, sig(history=None, started="2025-06"))
        self.assertEqual(d.decision, NO_MATCH)
        self.assertIn("no work history", d.reasons[0])

    def test_history_without_the_old_company_elsewhere_is_a_namesake(self):
        d = decide(CH, sig(city="Denver", history=("Contoso", "Adatum")))
        self.assertEqual(d.decision, NO_MATCH)
        self.assertIn("namesake", d.reasons[0])

    def test_history_without_the_old_company_in_the_same_city_is_held(self):
        d = decide(CH, sig(history=("Contoso", "Adatum")))
        self.assertEqual(d.decision, HOLD)
        self.assertIn("incomplete profile", d.reasons[0])

    def test_initial_only_is_held(self):
        self.assertEqual(decide(CH, sig(name="R. Chen")).decision, HOLD)

    def test_another_spelling_of_the_first_name_is_held_not_dropped(self):
        ch = Champion("c9", "Yevgenia Kharitonova", "Starkwell Mining", city="Riga")
        d = decide(ch, sig(name="Evgeniya Kharitonova", city="Riga", history=("Starkwell Mining",)))
        self.assertEqual(d.decision, HOLD)

    def test_started_new_job_long_before_last_seen_at_old_is_held(self):
        d = decide(CH, sig(started="2026-01"))
        self.assertEqual(d.decision, HOLD)
        self.assertIn("2026-03-10", d.reasons[0])

    def test_notice_period_overlap_is_fine(self):
        self.assertEqual(decide(CH, sig(started="2026-03")).decision, MATCH)

    def test_city_change_without_profile_is_held(self):
        self.assertEqual(decide(CH, sig(city="Denver")).decision, HOLD)

    def test_renamed_city_is_not_a_city_change(self):
        ch = Champion("c9", "Arjun Mehta", "Cindral Data", city="Bangalore")
        d = decide(ch, sig(name="Arjun Mehta", city="Bengaluru", history=("Cindral Data",)))
        self.assertEqual(d.decision, MATCH)

    def test_name_and_history_match_names_the_company_as_listed(self):
        groups = companies.alias_groups([("Northwind Travel", "Northwind")])
        d = decide(CH, sig(history=("Northwind",)), groups)
        self.assertEqual(d.decision, MATCH)
        self.assertEqual(d.proof, "name fits and Northwind Travel (listed as 'Northwind') is in their work history")


class Ambiguity(unittest.TestCase):
    def test_two_sure_matches_for_one_champion_are_both_held(self):
        ds = decide_case(CH, [sig(id="a"), sig(id="b", company="Contoso")])
        self.assertEqual([d.decision for d in ds], [HOLD, HOLD])
        self.assertTrue(all(d.proof is None for d in ds))

    def test_the_same_move_reported_twice_stays_a_match(self):
        ds = decide_case(CH, [sig(id="a"), sig(id="b", company="Fabrikam Ltd", profile=CH.profile, history=None)])
        self.assertEqual([d.decision for d in ds], [MATCH, MATCH])
        self.assertIn("reported 2 times", ds[0].reasons[-1])

    def test_one_match_and_one_namesake_keeps_the_match(self):
        ds = decide_case(CH, [sig(id="a"), sig(id="b", city="Denver", history=("Contoso",))])
        self.assertEqual([d.decision for d in ds], [MATCH, NO_MATCH])

    def test_one_signal_fitting_two_champions_is_held(self):
        twin = Champion("c2", "Robert Chen", "Northwind Travel", city="Austin")
        ds = run([CH, twin], [sig()])
        self.assertEqual([d.decision for d in ds], [HOLD, HOLD])

    def test_run_returns_only_alerts_and_holds(self):
        ds = run([CH], [sig(id="a"), sig(id="b", name="Siobhan Walsh")])
        self.assertEqual([(d.signal_id, d.decision) for d in ds], [("a", MATCH)])


if __name__ == "__main__":
    unittest.main()
