-- v49.23: the "chisme-media" bucket only allows image/webp (2 MB), but the server stores re-encoded videos there as
-- video/mp4 (v/YYYYMM/xxxx.mp4, up to ~40 MB), so Supabase Storage refuses every video upload. Photos (incl. profile
-- photos) are unaffected. Still server-only writes: no storage.objects policies for anon / authenticated are added.
-- Undo: set allowed_mime_types = array['image/webp'], file_size_limit = 2097152 on both buckets.
update storage.buckets
   set allowed_mime_types = array['image/webp', 'video/mp4'], file_size_limit = 41943040
 where id in ('chisme-media', 'chisme-quarantine');
