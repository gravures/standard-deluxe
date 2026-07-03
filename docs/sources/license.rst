=======
License
=======

Standard-Deluxe
_______________

Standard-deluxe is distributed under the term of the **GNU General Public License**.

.. include:: ../../LICENSE
   :literal:

Importer Module
_______________

:mod:`deluxe.importers` includes code derived from the Python :mod:`test.support.import_helper`
module Copyright (C) 2006 Python Software Foundation, licensed under
the ``PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2``. That module is part
of CPython's test suite and is not guaranteed to be available in all Python
distributions or to remain stable between releases (actually it is already
absent from some standalone Python build).
Those vendored portions have been adapted to fit ``standard-deluxe`` public API:
:class:`deluxe.importers.CleanImport`, :class:`deluxe.importers.DirsOnSysPath`, :func:`deluxe.importers.forget_module`, :func:`deluxe.importers.frozen_modules`, :func:`deluxe.importers.import_fresh_module`.

.. include:: ../../licenses/python_LICENSE
   :literal:
