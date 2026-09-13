"""Icon family context and immutable fonts protect incremental asset upgrades."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_fontawesome_subset as icons
import sync_social_meta as social
from generation_support import GenerationError


class IconSafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def test_dynamic_brand_icon_uses_existing_element_family(self):
        self.put('index.html', '<i id="social-icon" class="fa-brands"></i>')
        self.put('js/social.js', 'const icon = document.getElementById("social-icon"); icon.classList.add("fa-instagram");')
        self.assertEqual(icons.collect_icons(self.root), {'brands': {'instagram'}, 'solid': set(), 'regular': set()})

    def test_direct_selector_and_classname_assignment_resolve_family(self):
        self.put('index.html', '<i class="fa-brands"></i>')
        self.put('js/social.js', '''document.querySelector('.fa-brands').classList.add('fa-instagram');
            const icon = document.createElement('i'); icon.className = 'fa-regular'; icon.classList.add('fa-calendar');''')
        found = icons.collect_icons(self.root)
        self.assertEqual(found['brands'], {'instagram'})
        self.assertEqual(found['regular'], {'calendar'})

    def test_unknown_dynamic_family_requires_a_bounded_declaration(self):
        self.put('index.html', '<main>Congress</main>')
        script = self.put('js/social.js', 'icon.classList.add("fa-instagram");')
        with self.assertRaisesRegex(GenerationError, 'fontawesome-dynamic declaration'):
            icons.collect_icons(self.root)
        script.write_text('// fontawesome-dynamic: brands instagram\nicon.classList.add("fa-instagram");')
        self.assertEqual(icons.collect_icons(self.root)['brands'], {'instagram'})

    def test_inline_script_family_and_constructed_icon_names(self):
        self.put('index.html', '''<i id="icon" class="fa-brands"></i>
            <script>document.getElementById('icon').classList.add('fa-instagram');</script>''')
        self.assertEqual(icons.collect_icons(self.root)['brands'], {'instagram'})
        script = self.put('js/dynamic.js', 'icon.className = "fa-" + chosenIcon;')
        with self.assertRaisesRegex(GenerationError, 'constructed icon names'):
            icons.collect_icons(self.root)
        script.write_text('icon.classList.add(`fa-${chosenIcon}`);')
        with self.assertRaisesRegex(GenerationError, 'constructed icon names'):
            icons.collect_icons(self.root)
        script.write_text('// fontawesome-dynamic: brands instagram whatsapp\nicon.className = "fa-" + chosenIcon;')
        self.assertEqual(icons.collect_icons(self.root)['brands'], {'instagram', 'whatsapp'})

    def test_conflicting_declaration_cannot_override_target_family(self):
        self.put('index.html', '<i id="icon" class="fa-solid"></i>')
        self.put('js/social.js', '// fontawesome-dynamic: brands instagram\nconst icon = document.getElementById("icon"); icon.classList.add("fa-instagram");')
        with self.assertRaisesRegex(GenerationError, 'declaration conflicts'):
            icons.collect_icons(self.root)

    def test_changed_font_bytes_get_new_immutable_url_and_old_fonts_remain(self):
        self.put('index.html', '<i class="fa-solid fa-sun"></i>')
        self.put('vendor/fontawesome/all.min.css', '.fa-sun:before{content:"\\f185"}')
        legacy = self.put('vendor/fontawesome/webfonts/fa-solid-900-subset.woff2', 'cached old font')
        payload = [b'font version one']
        def build(command, **kwargs):
            output = Path(next(value.split('=', 1)[1] for value in command if value.startswith('--output-file=')))
            output.write_bytes(payload[0])
            return subprocess.CompletedProcess(command, 0, '', '')
        urls = []
        with patch.object(icons.importlib.util, 'find_spec', return_value=True), patch.object(icons, 'validate_glyphs'), patch.object(icons.subprocess, 'run', side_effect=build), redirect_stdout(io.StringIO()):
            for value in [b'font version one', b'font version two']:
                payload[0] = value
                icons.main(self.root)
                filename = 'fa-solid-900-subset.' + hashlib.sha256(value).hexdigest()[:16] + '.woff2'
                css = (self.root / 'vendor/fontawesome/fa-subset.min.css').read_text()
                self.assertIn('/vendor/fontawesome/webfonts/' + filename, css)
                self.assertEqual((self.root / 'vendor/fontawesome/webfonts' / filename).read_bytes(), value)
                urls.append(filename)
        self.assertNotEqual(*urls)
        self.assertTrue((self.root / 'vendor/fontawesome/webfonts' / urls[0]).is_file())
        self.assertEqual(legacy.read_text(), 'cached old font')

    def test_social_freshness_verifies_source_and_output_without_image_tools(self):
        source = self.put('images/photo.webp', 'source photograph')
        target = self.root / 'images/og/photo.jpg'
        target.parent.mkdir()
        target.write_bytes(b'\xff\xd8complete known JPEG fixture')
        record = {'source': 'images/photo.webp', 'source_sha256': social.digest(source),
                  'output_sha256': social.digest(target), 'recipe': social.RECIPE}
        self.put('images/og/generated-cards.json', json.dumps({'images/og/photo.jpg': record}))
        with patch.object(social, 'run_tool', side_effect=AssertionError('verification must not run image tools')):
            with social.CardBuild(self.root) as cards:
                cards.verify_card('/images/og/photo.jpg')
            source.write_text('replacement source')
            with social.CardBuild(self.root) as cards, self.assertRaisesRegex(GenerationError, 'generated social card is stale'):
                cards.verify_card('/images/og/photo.jpg')
        self.assertEqual(target.read_bytes(), b'\xff\xd8complete known JPEG fixture')

    def test_missing_or_corrupt_authored_social_card_fails_without_replacing_it(self):
        with social.CardBuild(self.root) as cards, self.assertRaisesRegex(GenerationError, 'required social JPG is missing'):
            cards.verify_card('/images/og/authored.jpg')
        target = self.put('images/og/authored.jpg', 'not a JPEG')
        with social.CardBuild(self.root) as cards, self.assertRaisesRegex(GenerationError, 'not encoded as JPEG'):
            cards.verify_card('/images/og/authored.jpg')
        self.assertEqual(target.read_text(), 'not a JPEG')


if __name__ == '__main__':
    unittest.main()
