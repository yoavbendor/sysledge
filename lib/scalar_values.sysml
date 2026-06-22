package ScalarValues {
    doc /*
     * Minimal stand-in for the SysML v2 standard ScalarValues library. The nomograph indexer does not
     * bundle the full standard library, so without this the primitive attribute types (String, Real, ...)
     * resolve to nothing and show up as dangling references. Declaring them here keeps `nomograph-sysml
     * check dangling-references` clean. Replace with the real standard library import if/when nomograph
     * ships one.
     */
    attribute def String;
    attribute def Real;
    attribute def Integer;
    attribute def Boolean;
}
