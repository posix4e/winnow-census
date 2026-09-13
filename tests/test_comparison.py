import importlib.util
import json
import gzip
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('compare', Path(__file__).resolve().parents[1]/'scripts/census_compare.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ComparisonTests(unittest.TestCase):
    def source(self, name, date='2026-09-13T10:00:00Z'):
        return dict(source=name, observationStart=date, observationEnd=date, endpoints=['8.8.8.8:8333', '9.9.9.9:8333'],
                    versionEndpoints=['8.8.8.8:8333', '9.9.9.9:8333'], compactFilterEndpoints=['8.8.8.8:8333'])

    def test_canonical_endpoint_and_overlay(self):
        self.assertEqual(module.endpoint('[::ffff:8.8.8.8]:8333'), '8.8.8.8:8333')
        self.assertEqual(module.endpoint('[2606:4700:0::1111]:8333'), '[2606:4700::1111]:8333')
        self.assertEqual(module.overlay('[fc00::1]:8333'), 'cjdns')
        self.assertEqual(module.overlay('name.onion:8333'), 'tor')

    def test_matched_denominator_and_shared_source(self):
        a,b = self.source('winnow'),self.source('btcnodes')
        b['compactFilterEndpoints'] = b['endpoints']
        result = module.comparison(a,b)
        self.assertEqual(result['denominator'],2)
        self.assertEqual(result['countDifference'],-1)
        self.assertEqual(result['percentagePointDifference'],-50)
        self.assertIn('not independent',result['reason'])
        self.assertEqual(result['endpointOverlap']['intersection'],2)

    def test_mismatched_window_missing_metrics_and_missing_timestamp(self):
        a,b=self.source('winnow'),self.source('21ninja','2025-11-04T00:00:00Z')
        self.assertIsNone(module.comparison(a,b)['percentagePointDifference'])
        b['observationStart']=None
        self.assertIsNone(module.comparison(a,b)['timestampDifferenceSeconds'])
        b=self.source('coindance');b.pop('versionEndpoints')
        self.assertIsNone(module.comparison(a,b)['countDifference'])

    def test_no_percentage_from_empty_population(self):
        a,b=self.source('winnow'),self.source('btcnodes')
        b['versionEndpoints']=['1.1.1.1:8333']
        self.assertIsNone(module.comparison(a,b)['percentagePointDifference'])

    def test_offset_normalization_and_complete_window_boundaries(self):
        a, b = self.source('winnow'), self.source('btcnodes', '2026-09-13T06:00:00-04:00')
        self.assertEqual(module.comparison(a, b)['timestampDifferenceSeconds'], 0)
        b['observationEnd'] = '2026-09-15T10:00:00Z'
        self.assertIsNone(module.comparison(a, b)['percentagePointDifference'])
        for end in [None, 'malformed', '2026-09-13T09:00:00Z', '2026-09-13T10:00:00']:
            a['observationEnd'] = end
            self.assertIsNone(module.comparison(a, b)['timestampDifferenceSeconds'])

    def test_fixture_normalization_and_unknown_markup(self):
        evidence=dict(url='fixture',sha256='a'*64,retrievedAt='2026-09-13T12:00:00Z',independence='shared input')
        raw=json.dumps(dict(timestamp=1789293600,nodes={'8.8.8.8:8333':[70016,'/Satoshi:30/',0,64,900000]})).encode()
        result=module.normalize('btcnodes',raw,evidence)
        self.assertEqual(result['stages']['advertisedCompactFilters'],1)
        self.assertEqual(result['software'],{'Core':1})
        self.assertIn('shared input',result['independence'])
        with self.assertRaises(ValueError): module.normalize('coindance',b'<html>changed markup</html>',evidence)

    def test_bitnodes_export_does_not_invent_observation_window(self):
        evidence=dict(url='fixture',sha256='a'*64,retrievedAt='2026-09-13T12:00:00Z',independence='same project')
        raw=b'export_date,ip_address,port,services,user_agent\n2026-07-03,::ffff:8.8.8.8,8333,64,/Satoshi:30/\n2026-09-13,9.9.9.9,8333,0,/Satoshi:30/\n'
        result=module.normalize('bitnodes_export',raw,evidence)
        self.assertIsNone(result['observationStart'])
        self.assertEqual(result['stages']['retainedExportEndpoints'],2)
        self.assertEqual(result['stages']['retainedAdvertisedCompactFilters'],1)
        self.assertEqual(result['rowExportDates'],{'2026-07-03':1,'2026-09-13':1})
        self.assertEqual(result['independenceAtCapture'],'same project')
        self.assertIn('own measurements',result['independence'])
        self.assertIn('not another independent source',result['independence'])
        self.assertTrue((Path(__file__).resolve().parents[1]/result['methodologyReference']).exists())
        compared=module.comparison(self.source('winnow'),result)
        self.assertEqual(compared['endpointOverlap']['intersection'],2)
        self.assertIsNone(compared['percentagePointDifference'])
        with self.assertRaises(ValueError):
            module.normalize('bitnodes_export',raw.replace(b'2026-07-03',b'2026-02-30'),evidence)
        with self.assertRaises(ValueError):
            module.normalize('bitnodes_export',raw+raw.splitlines(keepends=True)[1],evidence)

    def test_seed_export_keeps_observation_and_creation_distinct(self):
        evidence=dict(url='fixture',sha256='a'*64,retrievedAt='2026-09-13T12:00:00Z',independence='same project')
        raw=gzip.compress(b'# created by gravity on 2026-05-22T23:50:12Z with seed-exporter 1.2.2\n'
                          b'8.8.8.8:8333 1 1776949947 100% 100% 100% 100% 100% 946303 00000c49 70016 "/Satoshi:30.2.0/"\n'
                          b'example.b32.i2p:0 0 1776950000 0% 0% 0% 0% 0% 946303 00000c09 70016 "/Satoshi:30.2.0/"\n')
        result=module.normalize('21ninja_seeds',raw,evidence)
        self.assertIsNone(result['observationStart'])
        self.assertEqual(result['exportCreatedAt'],'2026-05-22T23:50:12Z')
        self.assertEqual(result['stages']['retainedAdvertisedCompactFilters'],1)
        self.assertEqual(result['overlays'],{'ipv4':1,'i2p':1})
        self.assertNotIn('versionEndpoints',result)
        self.assertIsNone(module.comparison(self.source('winnow'),result)['percentagePointDifference'])

    def test_bitnodes_retention_uses_calendar_days_not_scan_timestamp(self):
        evidence=dict(url='https://www.bitnod.es/csv/bitcoin_nodes_2026-09-13.csv',sha256='a'*64,
                      retrievedAt='2026-09-13T18:00:00Z',independence='same project')
        raw=b'export_date,ip_address,port,services,user_agent\n2026-09-04,8.8.8.8,8333,64,/Satoshi:30/\n2026-09-05,9.9.9.9,8333,64,/Satoshi:30/\n2026-09-13,1.1.1.1,8333,0,/Satoshi:30/\n2026-09-14,1.0.0.1,8333,64,/Satoshi:30/\n'
        result=module.normalize('bitnodes_export',raw,evidence)
        self.assertEqual(result['stages']['activeByPublishedRetention'],2)
        self.assertEqual(result['stages']['activeAdvertisedCompactFilters'],1)
        self.assertEqual(result['retentionFilteredEndpoints'],['1.1.1.1:8333','9.9.9.9:8333'])
        self.assertIsNone(result['observationStart'])
        self.assertEqual(module.comparison(self.source('winnow'),result)['retentionFilteredEndpointOverlap']['intersection'],1)
        delta=module.export_dashboard_comparison(result,{'stages':{'retainedReachable':3,'advertisedCompactFilters':2}})
        self.assertEqual(delta['addressCountDifference'],-1)
        self.assertEqual(delta['advertisedCompactFilterCountDifference'],-1)
        self.assertIsNone(delta['percentagePointDifference'])
        self.assertEqual(module.export_dashboard_comparison(result,{})['status'],'unavailable')

if __name__=='__main__': unittest.main()
