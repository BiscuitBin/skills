# Work is tracked in local Markdown, one ticket per file

Tickets live in the repository under `.scratch/<effort>/issues/`, one Markdown file per ticket, and are reviewed and changed in the same commits as the code they describe. An external tracker was the obvious alternative. It was rejected because every agent working here can read and update a file without credentials or a network call, and a ticket's history stays next to the diff that closed it.

Tracker text is not reformatted by the gate's formatters. Markdownlint reads it like any other Markdown, but nothing rewrites it.
