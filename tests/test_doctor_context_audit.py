import json
import unittest
from core import connect
from scripts.audit_doctor_context import audit


class DoctorAuditTest(unittest.TestCase):
    def test_choices_are_counted_without_doctor_attribution_or_raw_output(self):
        db = connect(":memory:")
        self.addCleanup(db.close)
        db.execute(
            "INSERT INTO stories VALUES('s','ko_KR','fixture','synthetic','test','')"
        )
        db.execute(
            "INSERT INTO lines VALUES('choice','s',0,'','PRIVATE_CHOICE','decision@0:synthetic','test')"
        )
        db.execute(
            "INSERT INTO lines VALUES('hit','s',1,'켈시','Mon3tr PRIVATE_LINE','main','test')"
        )
        report = audit(db)
        ko = report["languages"]["ko_KR"]
        self.assertEqual(ko["matching_lines"], 1)
        self.assertEqual(ko["with_choice_within_30_rows"], 1)
        self.assertEqual(ko["with_named_doctor_within_30_rows"], 0)
        self.assertNotIn("PRIVATE_", json.dumps(report))
        db.execute(
            "INSERT INTO lines VALUES('doctor','s',2,'박사','PRIVATE_DOCTOR','other','test')"
        )
        ko = audit(db)["languages"]["ko_KR"]
        self.assertEqual(ko["with_named_doctor_within_30_rows"], 1)
        self.assertEqual(ko["with_named_doctor_same_branch_within_30_rows"], 0)
