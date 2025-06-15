using UnityEngine;
using System.Collections;

public class ConveyorMovement : MonoBehaviour
{
    [Header("Movement Settings")]
    [SerializeField] private float speed = 3f;
    [SerializeField] private float stopPrecision = 0.001f;
    [SerializeField] private float inspectionPause = 2f;

    [Header("Route Points")]
    [SerializeField] private Transform inspectionPoint;
    [SerializeField] private Transform sortingPoint;
    [SerializeField] private Transform goodEndPoint;
    [SerializeField] private Transform defectiveEndPoint;

    private Vector3 currentTarget;
    private bool isInspecting;
    private bool hasDefects;

    void Start()
    {
        currentTarget = inspectionPoint.position;
    }

    void Update()
    {
        if (isInspecting) return;

        transform.position = Vector3.MoveTowards(
            transform.position,
            currentTarget,
            speed * Time.deltaTime
        );

        if (Vector3.Distance(transform.position, currentTarget) <= stopPrecision)
        {
            HandlePointReached();
        }
    }

    private void HandlePointReached()
    {
        if (currentTarget == inspectionPoint.position)
        {
            StartCoroutine(WaitForInspection());
        }
        else if (currentTarget == sortingPoint.position)
        {
            currentTarget = hasDefects ? defectiveEndPoint.position : goodEndPoint.position;
        }
        else
        {
            // Конец маршрута
            enabled = false;
        }
    }

    private IEnumerator WaitForInspection()
    {
        isInspecting = true;
        yield return new WaitForSeconds(inspectionPause);
        currentTarget = sortingPoint.position;
        isInspecting = false;
    }

    public void SetDefectStatus(bool defective)
    {
        hasDefects = defective;
        Debug.Log($"Defect status set to: {defective}");
    }
}