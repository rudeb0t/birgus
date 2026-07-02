# Birgus

<p align="center">
  <img src="birgus-mascot.png" width="400" alt="Birgus Mascot">
</p>

## What it is

Birgus is a lightweight, low-friction library for capturing tracebacks in
Python applications. It is designed to be easy to integrate into existing
codebases, providing developers with a simple way to log and analyze errors and
exceptions.

It is meant to be used in cases where you want to capture detailed traceback
information for later analysis, debugging, or reporting without the hassle of
setting up or paying for complex application monitoring services.

By default, Birgus captures the traceback of unhandled exceptions and dumps
them to a file using Cap'n Proto serialization.

## What it's not

Birgus is not meant to replace full-fledged application monitoring services
like Sentry or Datadog. If you can afford it, get Sentry, or set up a self-hosted
instance.

Only Python is supported for now.
