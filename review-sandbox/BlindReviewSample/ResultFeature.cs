namespace BlindReviewSample;

public sealed class ResultFeature
{
    public string? SampleSoiGlobalId { get; init; }
    public string? Geometry { get; init; }
    public Dictionary<string, string?> Attributes { get; } = new();
}
