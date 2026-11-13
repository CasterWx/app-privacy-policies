# Shared document repository

- The owner requested direct-link access with no prominent application or policy index. Keep the README and site landing page neutral. Do not add an app directory, direct policy links, sitemap, repository homepage link, or an “all apps” navigation to them.
- Keep policy sources and generated pages in the nested structure specified by `config/publication/catalog/registry.json`. Keep published `publicPath` values stable across text changes or app renames.
- Public GitHub files remain publicly readable and searchable. Deep paths and noindex directives are discoverability preferences, not authentication or access control. Never require a login to read a published privacy URL.
- Audit each app’s actual data flows and dependencies before writing its policy. Do not copy another app’s offline, no-collection, payment, tracking or retention claims without evidence.
- Keep review contacts, private email addresses, credentials, app saves and support tickets out of this repository. Publish only contact channels authorized as public.
- Update all published translations when practices change. Run `python3 scripts/build.py` and commit the policy sources and generated pages together. GitHub Pages serves `main:/docs`.
- Do not add analytics, remote fonts, advertisements, a feedback form or a backend without a new explicit product request and updated disclosure.
- Editing policies does not authorize app submission or changes to another app’s store metadata.
