import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mission_list import sort_rows,archive_state,timestamp,metadata

class Tests(unittest.TestCase):
 def test_sort_keeps_original_indices_and_missing_values_last(self):
  rows=[(0,{'name':'Gamma','distance':None}),(1,{'name':'Beta','distance':'20'}),(2,{'name':'Alpha','distance':10})]
  label=lambda i,m:m['name']
  self.assertEqual([i for i,_ in sort_rows(rows,'name-asc',label)],[2,1,0])
  self.assertEqual([i for i,_ in sort_rows(rows,'distance-desc',label)],[1,2,0])
  self.assertEqual([i for i,_ in sort_rows(rows,'distance-asc',label)],[2,1,0])
 def test_dates_accept_milliseconds_and_sort_newest_first(self):
  rows=[(0,{'updated':1700000000000}),(1,{'updated':1800000000}),(2,{'updated':None})]
  self.assertEqual([i for i,_ in sort_rows(rows,'date-desc',lambda i,m:'')],[1,0,2])
  self.assertEqual(timestamp(1700000000000),1700000000)
 def test_archive_status_requires_hash_and_loaded_archive(self):
  saved=[{'sha256':'same','name':'A different name'}]
  self.assertEqual(archive_state({'sha256':'same'},saved,True),'saved')
  self.assertEqual(archive_state({'sha256':'other'},saved,True),'missing')
  self.assertEqual(archive_state({'sha256':'same'},saved,False),'unknown')
  self.assertEqual(archive_state({'localState':'cloud-or-missing'},saved,True),'unknown')
 def test_invalid_metadata_is_not_fabricated(self):
  self.assertEqual(metadata({'distance':'not numeric','updated':None}),'')
