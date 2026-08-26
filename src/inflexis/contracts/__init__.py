"""Cross-plane data and interface contracts.

These modules define *what the platform agrees on*, independent of any
implementation, vendor, or storage engine. Implementations live elsewhere;
contracts live here so that a district deployment can swap an implementation
without renegotiating the meaning of a document, a role, or an audit record.
"""
